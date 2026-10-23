"""Run OpenFace sequentially with isolated output directories and durable logs."""

import os
import json
import subprocess
import time
import pandas as pd
from tqdm import tqdm
from .common import config, parser, save_json


def input_identity(video, binary):
    return {
        "video": str(video.resolve()),
        "video_size": video.stat().st_size,
        "video_mtime_ns": video.stat().st_mtime_ns,
        "binary": str(binary.resolve()),
        "binary_size": binary.stat().st_size,
        "binary_mtime_ns": binary.stat().st_mtime_ns,
        "arguments": ["-aus"],
    }


def extract(video, video_id, c, force=False):
    binary = c["openface_binary"]
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise FileNotFoundError(f"OpenFace executable unavailable: {binary}")
    out = c["paths"]["openface"] / video_id
    out.mkdir(exist_ok=True)
    csv = out / (video.stem + ".csv")
    identity = input_identity(video, binary)
    marker = out / "complete.json"
    try:
        cached_identity = json.loads(marker.read_text()) if marker.exists() else None
    except (OSError, ValueError):
        cached_identity = None
    if csv.exists() and cached_identity == identity and not force:
        check = pd.read_csv(csv, nrows=1)
        check.columns = check.columns.str.strip()
        if not any(x.startswith("AU") and x.endswith("_r") for x in check):
            raise ValueError(f"Invalid cached output: {csv}")
        return csv
    csv.unlink(missing_ok=True)
    (out / "complete.json").unlink(missing_ok=True)
    env = dict(
        os.environ,
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
    )
    with (out / "extraction.log").open("w") as log:
        subprocess.run(
            [str(binary), "-f", str(video.resolve()), "-aus", "-out_dir", str(out)],
            cwd=binary.parent,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=c["extraction_timeout"],
        )
    if not csv.exists():
        raise RuntimeError("OpenFace returned without CSV")
    check = pd.read_csv(csv, nrows=1)
    check.columns = check.columns.str.strip()
    if check.empty or not any(x.startswith("AU") and x.endswith("_r") for x in check):
        raise ValueError("Empty or invalid OpenFace CSV")
    save_json(out / "complete.json", identity)
    return csv


def main():
    p = parser(__doc__)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    c = config(a.config)
    df = pd.read_csv(c["paths"]["metadata"] / "videos.csv")
    rows = []
    for r in tqdm(df.itertuples(), total=len(df)):
        start = time.monotonic()
        try:
            path = extract(c["root"] / r.video_path, r.video_id, c, a.force)
            error = ""
            ok = True
        except Exception as e:
            path = ""
            error = str(e)
            ok = False
        rows.append(
            dict(
                video_id=r.video_id,
                success=ok,
                seconds=time.monotonic() - start,
                csv_path=str(path),
                error=error,
            )
        )
        manifest = c["paths"]["metadata"] / "extraction.csv"
        pd.DataFrame(rows).to_csv(manifest.with_suffix(".tmp"), index=False)
        manifest.with_suffix(".tmp").replace(manifest)
    save_json(
        c["paths"]["metadata"] / "extraction_summary.json",
        dict(
            videos=len(rows),
            successful=sum(r["success"] for r in rows),
            success_rate=sum(r["success"] for r in rows) / len(rows) if rows else 0,
            total_seconds=sum(r["seconds"] for r in rows),
        ),
    )
    print(f'Success: {sum(r["success"] for r in rows)}/{len(rows)}')


if __name__ == "__main__":
    main()
