"""Quality control retaining frame IDs and timestamps to detect gaps."""

import re
import numpy as np
import pandas as pd
from .common import config, parser, save_json


def clean(path, c):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    aus = sorted(x for x in df if re.fullmatch(r"AU\d+_r", x))
    required = ["frame", "timestamp", "success", "confidence"]
    if not aus or any(x not in df for x in required):
        raise ValueError("Missing AU or quality/time columns")
    df = (
        df[required + aus]
        .apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
    )
    if df.frame.dropna().duplicated().any():
        raise ValueError("Duplicate frames / multiple faces unsupported")
    mask = (
        (df.success == 1)
        & (df.confidence >= c["confidence"])
        & df[["frame", "timestamp"] + aus].notna().all(axis=1)
    )
    out = df.loc[mask, ["frame", "timestamp"] + aus].sort_values("timestamp").copy()
    if out.timestamp.duplicated().any():
        raise ValueError("Duplicate timestamps")
    ratio = len(out) / len(df) if len(df) else 0
    reasons = []
    if ratio < c["valid_ratio"]:
        reasons.append("low_valid_ratio")
    if len(out) < 2:
        reasons.append("insufficient_frames")
    report = dict(
        total_frames=len(df),
        valid_frames=len(out),
        valid_ratio=ratio,
        failed_detection=int((df.success != 1).sum()),
        low_confidence=int((df.confidence < c["confidence"]).sum()),
        missing_frames=int(df.isna().any(axis=1).sum()),
        accepted=not reasons,
        reason=";".join(reasons),
    )
    return out, report


def main():
    p = parser(__doc__)
    p.add_argument("--confidence", type=float)
    p.add_argument("--valid-ratio", type=float)
    a = p.parse_args()
    c = config(a.config)
    if a.confidence is not None:
        c["confidence"] = a.confidence
    if a.valid_ratio is not None:
        c["valid_ratio"] = a.valid_ratio
    if not 0 <= c["confidence"] <= 1 or not 0 <= c["valid_ratio"] <= 1:
        raise ValueError("Thresholds must lie in [0,1]")
    manifest = pd.read_csv(c["paths"]["metadata"] / "extraction.csv")
    rows = []
    for r in manifest.itertuples():
        try:
            if not r.success:
                raise ValueError("extraction_failed")
            df, report = clean(r.csv_path, c)
            dest = c["paths"]["processed"] / f"{r.video_id}.csv"
            dest.unlink(missing_ok=True)
            if report["accepted"]:
                df.to_csv(dest, index=False)
        except Exception as e:
            report = dict(accepted=False, reason=str(e))
        rows.append(dict(video_id=r.video_id, **report))
    pd.DataFrame(rows).to_csv(c["paths"]["metadata"] / "quality.csv", index=False)
    save_json(
        c["paths"]["processed"] / "preprocessing.json",
        {
            k: c[k]
            for k in (
                "confidence",
                "valid_ratio",
                "activation_threshold",
                "max_gap_seconds",
            )
        },
    )


if __name__ == "__main__":
    main()
