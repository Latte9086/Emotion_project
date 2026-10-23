"""Small GRU over contiguous AU windows; supervised loss is per video."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_sequence
from sklearn.metrics import balanced_accuracy_score

from .common import config, parser, save_json
from .sequence_data import make_sequence, shuffled_sequence, read_partitions
from .evaluate import metrics, plots


class VideoGRU(nn.Module):
    def __init__(self, features, hidden):
        super().__init__()
        self.gru = nn.GRU(features, hidden, batch_first=True)
        self.classifier = nn.Linear(hidden, 1)

    def forward(self, videos):
        windows = [
            torch.as_tensor(w, dtype=torch.float32) for ws, _ in videos for w in ws
        ]
        lengths = torch.tensor([len(w) for w in windows], dtype=torch.long)
        packed = pack_padded_sequence(
            pad_sequence(windows, batch_first=True),
            lengths,
            batch_first=True,
            enforce_sorted=False,
        )
        _, states = self.gru(packed)
        logits = self.classifier(states[-1]).flatten()
        output = []
        start = 0
        for ws, weights in videos:
            w = torch.as_tensor(weights, dtype=torch.float32)
            output.append((logits[start : start + len(ws)] * w).sum() / w.sum())
            start += len(ws)
        return torch.stack(output)


def fit_normalizer(videos):
    values = np.concatenate([w for ws, _ in videos for w in ws])
    mean = values.mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = values.std(axis=0, dtype=np.float64).astype(np.float32)
    scale[scale < 1e-6] = 1
    return mean, scale


def normalize(videos, mean, scale):
    return [([(w - mean) / scale for w in ws], weights) for ws, weights in videos]


def fit(videos, y, settings, decay, seed):
    torch.set_num_threads(int(settings["threads"]))
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    mean, scale = fit_normalizer(videos)
    data = normalize(videos, mean, scale)
    model = VideoGRU(len(mean), int(settings["hidden_size"]))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(settings["learning_rate"]),
        weight_decay=float(decay),
    )
    labels = torch.tensor(y, dtype=torch.float32)
    counts = np.bincount(np.asarray(y, dtype=int), minlength=2)
    if counts.min() == 0:
        raise ValueError("Training requires both classes")
    class_weights = torch.tensor(len(y) / (2 * counts), dtype=torch.float32)
    rng = np.random.default_rng(seed)
    model.train()
    for _ in range(int(settings["epochs"])):
        order = rng.permutation(len(data))
        for start in range(0, len(data), int(settings["batch_videos"])):
            ids = order[start : start + int(settings["batch_videos"])]
            optimizer.zero_grad()
            logits = model([data[i] for i in ids])
            loss = nn.functional.binary_cross_entropy_with_logits(
                logits, labels[ids], reduction="none"
            )
            loss = (loss * class_weights[labels[ids].long()]).mean()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
    model.eval()
    return model, mean, scale


def scores(fitted, videos, batch=16):
    model, mean, scale = fitted
    data = normalize(videos, mean, scale)
    with torch.no_grad():
        return np.concatenate(
            [
                torch.sigmoid(model(data[i : i + batch])).numpy()
                for i in range(0, len(data), batch)
            ]
        )


def select(videos, y, folds, settings, seed):
    candidates = []
    for decay in settings["weight_decays"]:
        values = []
        for tr, va in folds:
            fitted = fit([videos[i] for i in tr], y[tr], settings, decay, seed)
            p = scores(fitted, [videos[i] for i in va])
            values.append(balanced_accuracy_score(y[va], p >= 0.5))
        candidates.append(
            dict(
                weight_decay=float(decay),
                inner_balanced_accuracy=float(np.mean(values)),
            )
        )
    best = max(candidates, key=lambda v: v["inner_balanced_accuracy"])
    return best["weight_decay"], candidates


def save_model(path, fitted, columns, settings, decay, c, scope, shuffle):
    model, mean, scale = fitted
    torch.save(
        dict(
            state_dict=model.state_dict(),
            mean=mean.tolist(),
            scale=scale.tolist(),
            columns=columns,
            temporal=dict(settings),
            weight_decay=decay,
            seed=c["seed"],
            shuffle=shuffle,
            evaluation_scope=scope,
            torch_version=str(torch.__version__),
            preprocessing={
                k: c[k]
                for k in (
                    "confidence",
                    "valid_ratio",
                    "activation_threshold",
                    "max_gap_seconds",
                )
            },
        ),
        path,
    )


def predict_video(video, model_path, c):
    from .extract_au import extract
    from .preprocess import clean

    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    c = dict(c, **artifact["preprocessing"])
    with video.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()[:16]
    csv = extract(video, "prediction_" + digest, c)
    df, quality = clean(csv, c)
    if not quality["accepted"]:
        return dict(prediction=None, reason=quality["reason"], quality=quality)
    try:
        sequence = make_sequence(
            df, artifact["columns"], artifact["temporal"], c["max_gap_seconds"]
        )
    except ValueError as e:
        return dict(prediction=None, reason=str(e), quality=quality)
    if artifact["shuffle"]:
        sequence = shuffled_sequence(sequence, artifact["seed"])
    torch.set_num_threads(int(artifact["temporal"]["threads"]))
    net = VideoGRU(len(artifact["columns"]), int(artifact["temporal"]["hidden_size"]))
    net.load_state_dict(artifact["state_dict"])
    net.eval()
    fitted = (
        net,
        np.asarray(artifact["mean"], dtype=np.float32),
        np.asarray(artifact["scale"], dtype=np.float32),
    )
    score = float(scores(fitted, [sequence])[0])
    return dict(
        prediction="Lie" if score >= 0.5 else "Truth",
        lie_score=score,
        truth_score=1 - score,
        calibrated=False,
        score_type="uncalibrated GRU sigmoid",
        evaluation_scope=artifact["evaluation_scope"],
        quality=quality,
        windows=len(sequence[0]),
    )


def experiment(c):
    settings = c["temporal"]
    df = pd.read_csv(c["paths"]["processed"] / "features_A.csv")
    stored = json.loads((c["paths"]["processed"] / "feature_settings.json").read_text())
    c = dict(c, **stored)
    columns = [x[:-5] + "_r" for x in df if x.endswith("_mean")]
    videos = [
        make_sequence(
            pd.read_csv(c["paths"]["processed"] / f"{vid}.csv"),
            columns,
            settings,
            c["max_gap_seconds"],
        )
        for vid in df.video_id
    ]
    folds, scope = read_partitions(df, c)
    y = df.label.to_numpy(dtype=int)
    summary = []
    rows = []
    predictions = []
    variants = [("GRU", False)] + (
        [("GRU_shuffled", True)] if settings["shuffle_control"] else []
    )
    for name, shuffle in variants:
        data = [shuffled_sequence(v, c["seed"]) for v in videos] if shuffle else videos
        for fold, (tr, te, inner) in enumerate(folds):
            print(f"{name}: outer fold {fold+1}/{len(folds)}", flush=True)
            train_data = [data[i] for i in tr]
            decay, search = select(train_data, y[tr], inner, settings, c["seed"])
            fitted = fit(train_data, y[tr], settings, decay, c["seed"])
            p = scores(fitted, [data[i] for i in te])
            rows.append(
                dict(
                    model=name,
                    feature_set="temporal",
                    fold=fold,
                    **metrics(y[te], p >= 0.5, p),
                )
            )
            predictions.extend(
                dict(
                    model=name,
                    feature_set="temporal",
                    fold=fold,
                    video_id=df.video_id.iloc[i],
                    label=int(y[i]),
                    prediction=int(s >= 0.5),
                    score=float(s),
                )
                for i, s in zip(te, p)
            )
            save_json(
                c["paths"]["results"] / "metrics" / f"{name}_{fold}_search.json", search
            )
            save_model(
                c["paths"]["models"] / f"{name}_fold_{fold}.pt",
                fitted,
                columns,
                settings,
                decay,
                c,
                scope,
                shuffle,
            )
            pd.DataFrame(rows).to_csv(
                c["paths"]["results"] / "metrics" / "folds_temporal.csv", index=False
            )
            pd.DataFrame(predictions).to_csv(
                c["paths"]["results"] / "metrics" / "predictions_temporal.csv",
                index=False,
            )
        from .train import splits

        groups = (
            df.person_id.astype(str).to_numpy() if df.person_id.notna().all() else None
        )
        inner = splits(y, groups, c["inner_folds"], c["seed"])
        decay, search = select(data, y, inner, settings, c["seed"])
        fitted = fit(data, y, settings, decay, c["seed"])
        save_model(
            c["paths"]["models"] / f"{name}.pt",
            fitted,
            columns,
            settings,
            decay,
            c,
            scope,
            shuffle,
        )
        save_json(
            c["paths"]["results"] / "metrics" / f"{name}_final_search.json", search
        )
    m = pd.DataFrame(rows)
    values = ["accuracy", "precision", "recall", "f1", "balanced_accuracy", "roc_auc"]
    temporal = m.groupby(["model", "feature_set"])[values].agg(["mean", "std"])
    temporal.columns = ["_".join(x) for x in temporal.columns]
    temporal = temporal.reset_index()
    comparison = pd.concat(
        [pd.read_csv(c["paths"]["results"] / "tables" / "comparison.csv"), temporal],
        ignore_index=True,
    )
    comparison.to_csv(
        c["paths"]["results"] / "tables" / "comparison_temporal.csv", index=False
    )
    plots(pd.DataFrame(predictions), "temporal", c)
    import matplotlib.pyplot as plt

    show = comparison[
        (comparison.feature_set == "C") | (comparison.feature_set == "temporal")
    ].copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    names = show.model + " / " + show.feature_set
    ax.bar(names, show.balanced_accuracy_mean, yerr=show.balanced_accuracy_std)
    ax.tick_params(axis="x", rotation=20)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Balanced accuracy (outer-fold mean ± SD)")
    fig.tight_layout()
    fig.savefig(c["paths"]["results"] / "figures" / "temporal_comparison.png")
    plt.close(fig)
    baseline = comparison[
        (comparison.model == "SVM") & (comparison.feature_set == "C")
    ].iloc[0]
    lines = [
        "# AU時系列モデルの実験結果",
        "",
        f"{len(df)}動画、外側{len(folds)}fold。元モデルと同一の外側・内側分割。人物IDなしの場合は人物リーク未解決の動画単位暫定評価。",
        "",
        f"{settings['sample_hz']}Hz、最大{settings['window_seconds']}秒の窓、小さなGRU（hidden={settings['hidden_size']}）、{settings['epochs']}epoch。窓は元動画内で集約して動画単位で学習・評価。欠損区間では系列を区切る。8秒を超える窓間の順序は学習しない。",
        "",
        "| Model | Accuracy mean ± SD | Balanced accuracy mean ± SD | ROC-AUC mean ± SD |",
        "|---|---|---|---|",
    ]
    for r in pd.concat([pd.DataFrame([baseline]), temporal]).itertuples():
        lines.append(
            f"| {r.model} | {r.accuracy_mean:.3f} ± {r.accuracy_std:.3f} | {r.balanced_accuracy_mean:.3f} ± {r.balanced_accuracy_std:.3f} | {r.roc_auc_mean:.3f} ± {r.roc_auc_std:.3f} |"
        )
    lines += [
        "",
        "GRU_shuffledは各窓内のAU行の順番を乱した対照。単一seed・少量データの探索的比較であり、モデル差の有意性、精度向上、未知人物への汎化は保証しない。各クラス・動画・人物の分割を維持し、標準化は各訓練foldのみで学習。較正していない分類スコア。",
        "",
        f"![比較]({c['paths']['results']/'figures'/'temporal_comparison.png'})",
    ]
    (c["root"] / "TEMPORAL_REPORT.md").write_text("\n".join(lines) + "\n")
    inputs = [c["paths"]["processed"] / f"{vid}.csv" for vid in df.video_id]
    save_json(
        c["paths"]["results"] / "metrics" / "temporal_provenance.json",
        dict(
            settings=settings,
            preprocessing=stored,
            seed=c["seed"],
            torch_version=str(torch.__version__),
            scope=scope,
            sequence_sha256={
                p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
            },
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        ),
    )
    print(temporal.to_string(index=False), flush=True)
    return temporal


def main():
    a = parser(__doc__).parse_args()
    experiment(config(a.config))


if __name__ == "__main__":
    main()
