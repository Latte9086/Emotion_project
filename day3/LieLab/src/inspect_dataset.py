"""Discover videos and explicit labels. Unknown labels remain missing."""

import json
import os
import re
import subprocess
from pathlib import Path
import pandas as pd
from .common import config, parser

LABELS = {"lie": 1, "deceptive": 1, "truth": 0, "truthful": 0, "1": 1, "0": 0}


def normalize_label(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    return LABELS.get(str(value).strip().lower())


def duration(path):
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None


def inspect(c, labels_file=None):
    root = c["paths"]["raw"]
    mappings = {}
    sources = [labels_file] if labels_file else sorted(root.rglob("*.csv"))
    for file in sources:
        if "__MACOSX" in Path(file).parts or Path(file).name.startswith("._"):
            continue
        try:
            table = pd.read_csv(file, dtype={"person_id": "string"})
            table.columns = table.columns.str.strip().str.lower()
        except Exception:
            if labels_file:
                raise
            continue
        idcol = next(
            (x for x in ("video_id", "id", "filename", "video") if x in table), None
        )
        labelcol = next((x for x in ("label", "class") if x in table), None)
        if not idcol or not labelcol:
            if labels_file:
                raise ValueError(
                    "Label CSV requires video_id/id/filename/video and label/class"
                )
            continue
        for _, row in table.iterrows():
            vid = Path(str(row[idcol])).stem
            lab = normalize_label(row[labelcol])
            if lab is None:
                raise ValueError(f"Unknown explicit label: {row[labelcol]}")
            person = row.get("person_id", None)
            person = (
                None
                if pd.isna(person) or not str(person).strip()
                else str(person).strip()
            )
            val = (lab, person, str(file))
            if vid in mappings:
                if mappings[vid][0] != lab:
                    raise ValueError(f"Conflicting labels: {vid}")
                old_person = mappings[vid][1]
                if (
                    old_person is not None
                    and person is not None
                    and old_person != person
                ):
                    raise ValueError(f"Conflicting person IDs: {vid}")
                if person is None and old_person is not None:
                    val = mappings[vid]
            mappings[vid] = val
    rows = []
    seen = set()
    for path in sorted(root.rglob("*")):
        if "__MACOSX" in path.parts or path.name.startswith("._"):
            continue
        if path.suffix.lower() not in {
            ".mp4",
            ".avi",
            ".wmv",
            ".mov",
            ".mkv",
            ".mpeg",
            ".mpg",
        }:
            continue
        vid = path.stem
        if vid in seen:
            raise ValueError(f"Duplicate video_id {vid}; rename or provide unique IDs")
        seen.add(vid)
        # Only explicit corpus class markers, never numeric suffixes/person identities.
        markers = {
            LABELS[t]
            for t in re.split(r"[^a-z]+", str(path.relative_to(root)).lower())
            if t in {"deceptive", "truthful"}
        }
        entry = mappings.get(vid)
        if len(markers) > 1 or (entry and markers and entry[0] not in markers):
            raise ValueError(f"Conflicting labels: {vid}")
        label, person, source = (
            entry
            if entry
            else (
                next(iter(markers)) if markers else None,
                None,
                "explicit class path" if markers else "unknown",
            )
        )
        rows.append(
            dict(
                video_id=vid,
                video_path=os.path.relpath(path, c["root"]),
                label=label,
                person_id=person,
                duration=duration(path),
                label_source=source,
            )
        )
    df = pd.DataFrame(
        rows,
        columns=[
            "video_id",
            "video_path",
            "label",
            "person_id",
            "duration",
            "label_source",
        ],
    )
    df.to_csv(c["paths"]["metadata"] / "videos.csv", index=False)
    files = [
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file()
        and any(
            s in p.name.lower() for s in ("readme", "license", "terms", "annotation")
        )
    ]
    (c["paths"]["metadata"] / "inventory.json").write_text(
        json.dumps(
            {
                "videos": len(df),
                "unknown_labels": int(df.label.isna().sum()),
                "terms_and_annotations": files,
            },
            indent=2,
        )
    )
    print(
        f'{len(df)} videos; {df.label.isna().sum()} unknown labels. Metadata: {c["paths"]["metadata"]}'
    )
    return df


def main():
    p = parser(__doc__)
    p.add_argument("--labels", help="CSV: video_id,label,person_id (optional)")
    a = p.parse_args()
    inspect(config(a.config), a.labels)


if __name__ == "__main__":
    main()
