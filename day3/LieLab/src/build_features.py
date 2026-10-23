"""AU-only video features; temporal differences use adjacent valid original frames."""

import numpy as np
import pandas as pd
from .common import config, parser, save_json


def features(df, c, kind):
    result = {}
    t = df.timestamp.to_numpy()
    dt = np.diff(t)
    adjacent = (
        (np.diff(df.frame.to_numpy()) == 1) & (dt > 0) & (dt <= c["max_gap_seconds"])
    )
    for au in sorted(x for x in df if x.startswith("AU") and x.endswith("_r")):
        x = df[au].to_numpy(dtype=float)
        key = au[:-2]
        result[key + "_mean"] = float(np.mean(x))
        if kind in "BC":
            result.update(
                {
                    key + "_std": float(np.std(x)),
                    key + "_max": float(np.max(x)),
                    key + "_median": float(np.median(x)),
                    key + "_q75": float(np.quantile(x, 0.75)),
                }
            )
        if kind == "C":
            delta = np.diff(x)[adjacent]
            times = dt[adjacent]
            result[key + "_delta_abs_mean"] = (
                float(np.abs(delta).mean()) if len(delta) else np.nan
            )
            result[key + "_delta_std"] = float(delta.std()) if len(delta) else np.nan
            result[key + "_active_time_fraction"] = (
                float(
                    np.sum(times * (x[:-1][adjacent] > c["activation_threshold"]))
                    / times.sum()
                )
                if len(times)
                else np.nan
            )
            result[key + "_derivative_abs_mean"] = (
                float(np.abs(delta).sum() / times.sum()) if len(times) else np.nan
            )
    return result


def main():
    a = parser(__doc__).parse_args()
    c = config(a.config)
    import json

    settings = json.loads((c["paths"]["processed"] / "preprocessing.json").read_text())
    c.update({k: settings[k] for k in ("confidence", "valid_ratio")})
    save_json(
        c["paths"]["processed"] / "feature_settings.json",
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
    meta = pd.read_csv(c["paths"]["metadata"] / "videos.csv")
    quality = pd.read_csv(c["paths"]["metadata"] / "quality.csv")
    accepted = set(quality.loc[quality.accepted == True, "video_id"])
    for kind in "ABC":
        rows = []
        for r in meta.itertuples():
            if r.video_id not in accepted or pd.isna(r.label):
                continue
            df = pd.read_csv(c["paths"]["processed"] / f"{r.video_id}.csv")
            rows.append(
                dict(
                    video_id=r.video_id,
                    person_id=r.person_id,
                    label=int(r.label),
                    **features(df, c, kind),
                )
            )
        pd.DataFrame(rows).to_csv(
            c["paths"]["processed"] / f"features_{kind}.csv", index=False
        )
        print(f"{kind}: {len(rows)} videos")


if __name__ == "__main__":
    main()
