"""AU window preparation and checked video/person CV splits, without PyTorch."""

import hashlib
import json
import numpy as np
import pandas as pd
from .common import save_json


def make_sequence(df, columns, settings, max_gap):
    """Interpolate inside valid original-frame runs only, never across missing frames."""
    hz = float(settings["sample_hz"])
    size = int(round(hz * settings["window_seconds"]))
    if hz <= 0 or size < 2 or max_gap <= 0:
        raise ValueError(
            "Positive sample rate/gap and at least two steps per window required"
        )
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError("Missing required AU columns: " + ",".join(sorted(missing)))
    t = df.timestamp.to_numpy(dtype=float)
    frames = df.frame.to_numpy(dtype=float)
    x = df[columns].to_numpy(dtype=np.float32)
    if not len(t) or not np.isfinite(x).all() or not np.isfinite(t).all():
        raise ValueError("Empty/nonfinite AU sequence")
    dt = np.diff(t)
    if np.any(dt <= 0):
        raise ValueError("Timestamps must strictly increase")
    breaks = np.flatnonzero((np.diff(frames) != 1) | (dt > max_gap)) + 1
    native_dt = (
        float(np.median(dt[(np.diff(frames) == 1) & (dt <= max_gap)]))
        if np.any((np.diff(frames) == 1) & (dt <= max_gap))
        else 1 / hz
    )
    windows, weights = [], []
    for indices in np.split(np.arange(len(t)), breaks):
        times = t[indices] - t[indices[0]]
        grid = np.arange(0, times[-1] + 1e-9, 1 / hz)
        values = np.column_stack(
            [np.interp(grid, times, x[indices, j]) for j in range(x.shape[1])]
        ).astype(np.float32)
        duration = max(float(times[-1]), native_dt)
        for start in range(0, len(values), size):
            window = values[start : start + size].copy()
            windows.append(window)
            weights.append(duration * len(window) / len(values))
    return windows, np.asarray(weights, dtype=np.float32)


def shuffled_sequence(sequence, seed):
    """Deterministic content-based shuffling keeps AU combinations and window lengths."""
    windows, weights = sequence
    result = []
    for window in windows:
        digest = int.from_bytes(hashlib.sha256(window.tobytes()).digest()[:8], "little")
        rng = np.random.default_rng((seed + digest) % (2**64))
        result.append(window[rng.permutation(len(window))].copy())
    return result, weights.copy()


def read_partitions(df, c, save_name="temporal.json"):
    """Reuse the exact baseline outer AND inner partitions; reject stale data/scope."""
    split = json.loads((c["paths"]["splits"] / "C.json").read_text())
    index = {v: i for i, v in enumerate(df.video_id)}
    if df.video_id.duplicated().any() or not df.label.isin([0, 1]).all():
        raise ValueError("Invalid video IDs/labels")
    if df.person_id.notna().any() and df.person_id.isna().any():
        raise ValueError("Partially missing person IDs")
    grouped = df.person_id.notna().all()
    if grouped != (split["scope"] == "person"):
        raise ValueError("Baseline grouping differs: rerun src.train first")

    def indices(ids):
        return np.asarray([index[v] for v in ids], dtype=int)

    folds = []
    all_tests = []
    for fold in split["folds"]:
        tr, te = indices(fold["train"]), indices(fold["test"])
        if (
            len(set(tr)) != len(tr)
            or len(set(te)) != len(te)
            or set(tr) & set(te)
            or set(tr) | set(te) != set(range(len(df)))
        ):
            raise ValueError("Invalid baseline outer split")
        if grouped and set(df.person_id.iloc[tr]) & set(df.person_id.iloc[te]):
            raise ValueError("Person leakage")
        local = {v: i for i, v in enumerate(tr)}
        inner = []
        for part in fold["inner"]:
            a, b = indices(part["train"]), indices(part["validation"])
            if set(a) & set(b) or set(a) | set(b) != set(tr):
                raise ValueError("Invalid baseline inner split")
            if grouped and set(df.person_id.iloc[a]) & set(df.person_id.iloc[b]):
                raise ValueError("Inner person leakage")
            inner.append(
                (np.asarray([local[v] for v in a]), np.asarray([local[v] for v in b]))
            )
        folds.append((tr, te, inner))
        all_tests.extend(te.tolist())
    if sorted(all_tests) != list(range(len(df))):
        raise ValueError("Outer predictions must cover each video once")
    previous = pd.read_csv(c["paths"]["results"] / "metrics" / "predictions_C.csv")
    for _, rows in previous.groupby("model"):
        if len(rows) != len(df) or set(rows.video_id) != set(index):
            raise ValueError("Baseline predictions do not match current cohort")
        if any(
            int(r.label) != int(df.label.iloc[index[r.video_id]])
            for r in rows.itertuples()
        ):
            raise ValueError("Baseline labels differ")
    save_json(c["paths"]["splits"] / save_name, split)
    return folds, split["scope"]
