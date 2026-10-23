"""Train MiniRocketMultivariate + video-level ridge classifier with nested CV."""

import hashlib
import importlib.metadata
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
from sktime.transformations.rocket import MiniRocketMultivariate

from .common import config, parser, save_json
from .evaluate import metrics, plots
from .sequence_data import make_sequence, read_partitions
from .train import splits


def panel(videos, settings):
    """Edge padding extends each window separately; observed-time weights stay unchanged."""
    length = int(round(settings["sample_hz"] * settings["window_seconds"]))
    if length < 9:
        raise ValueError("MiniRocket requires at least 9 timepoints per window")
    arrays = []
    counts = []
    for windows, weights in videos:
        if (
            not windows
            or len(windows) != len(weights)
            or np.any(weights <= 0)
            or not np.isfinite(weights).all()
        ):
            raise ValueError("Empty windows or invalid duration weights")
        counts.append(len(windows))
        for window in windows:
            if not 0 < len(window) <= length or not np.isfinite(window).all():
                raise ValueError("Invalid window length/values")
            padded = np.pad(window, ((0, length - len(window)), (0, 0)), mode="edge")
            arrays.append(padded.T)
    return np.stack(arrays).astype(np.float32), counts


def aggregate(transformed, videos, counts):
    z = np.asarray(transformed, dtype=np.float64)
    if len(z) != sum(counts):
        raise ValueError("Window feature count mismatch")
    rows = []
    start = 0
    for (_, weights), count in zip(videos, counts):
        rows.append(
            np.average(
                z[start : start + count], axis=0, weights=weights.astype(np.float64)
            )
        )
        start += count
    return np.stack(rows)


class VideoMiniRocket:
    """MiniRocket bias fitting and PPV scaling only see training videos."""

    def __init__(self, settings, seed=42):
        self.settings = dict(settings)
        self.seed = seed

    def fit_features(self, videos):
        X, counts = panel(videos, self.settings)
        self.transformer = MiniRocketMultivariate(
            num_kernels=int(self.settings["num_kernels"]),
            max_dilations_per_kernel=int(self.settings["max_dilations_per_kernel"]),
            n_jobs=int(self.settings["n_jobs"]),
            random_state=int(self.seed),
        )
        self.transformer.fit(X)
        features = aggregate(self.transformer.transform(X), videos, counts)
        self.scaler = StandardScaler().fit(features)
        self.training_videos = len(videos)
        self.training_windows = len(X)
        return self.scaler.transform(features)

    def transform(self, videos):
        X, counts = panel(videos, self.settings)
        return self.scaler.transform(
            aggregate(self.transformer.transform(X), videos, counts)
        )

    def fit(self, videos, y, alpha):
        features = self.fit_features(videos)
        self.classifier = RidgeClassifier(
            alpha=float(alpha), class_weight="balanced"
        ).fit(features, y)
        self.alpha = float(alpha)
        return self

    def decision_function(self, videos):
        return self.classifier.decision_function(self.transform(videos))

    def predict(self, videos):
        return self.classifier.predict(self.transform(videos))


def select(videos, y, inner, settings, seed):
    values = {float(a): [] for a in settings["alphas"]}
    if not values or min(values) <= 0:
        raise ValueError("Positive ridge alpha candidates required")
    for tr, va in inner:
        extractor = VideoMiniRocket(settings, seed)
        X = extractor.fit_features([videos[i] for i in tr])
        validation = extractor.transform([videos[i] for i in va])
        for alpha in values:
            model = RidgeClassifier(alpha=alpha, class_weight="balanced").fit(X, y[tr])
            values[alpha].append(
                balanced_accuracy_score(y[va], model.predict(validation))
            )
    records = [
        dict(alpha=a, inner_balanced_accuracy=float(np.mean(v)), inner_fold_scores=v)
        for a, v in values.items()
    ]
    best = max(records, key=lambda r: r["inner_balanced_accuracy"])
    return best["alpha"], records


def save_model(path, model, columns, c, scope, train_ids):
    joblib.dump(
        dict(
            model_type="minirocket",
            model=model,
            columns=columns,
            settings=model.settings,
            preprocessing={
                k: c[k]
                for k in (
                    "confidence",
                    "valid_ratio",
                    "activation_threshold",
                    "max_gap_seconds",
                )
            },
            evaluation_scope=scope,
            score_type="uncalibrated ridge decision_function",
            training_video_ids=list(train_ids),
            versions={
                n: importlib.metadata.version(n)
                for n in ("sktime", "numba", "scikit-learn", "numpy")
            },
        ),
        path,
    )


def predict_video(video, artifact, c):
    from .extract_au import extract
    from .preprocess import clean

    c = dict(c, **artifact["preprocessing"])
    with video.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()[:16]
    csv = extract(video, "prediction_" + digest, c)
    df, quality = clean(csv, c)
    if not quality["accepted"]:
        return dict(prediction=None, reason=quality["reason"], quality=quality)
    try:
        sequence = make_sequence(
            df, artifact["columns"], artifact["settings"], c["max_gap_seconds"]
        )
    except ValueError as e:
        return dict(prediction=None, reason=str(e), quality=quality)
    model = artifact["model"]
    score = float(model.decision_function([sequence])[0])
    label = int(model.predict([sequence])[0])
    return dict(
        prediction="Lie" if label else "Truth",
        lie_decision_score=score,
        score_type=artifact["score_type"],
        calibrated=False,
        evaluation_scope=artifact["evaluation_scope"],
        quality=quality,
        windows=len(sequence[0]),
    )


def write_report(comparison, c, n, scope, settings, folds):
    selected = comparison[
        ((comparison.model == "SVM") & (comparison.feature_set == "C"))
        | comparison.model.isin(["GRU", "GRU_shuffled", "MiniRocket"])
    ]
    lines = [
        "# MiniRocketの実データ比較",
        "",
        f"{n}動画。元のC＋SVMと同一の外側{len(folds)}fold・内側分割。評価範囲: {scope}。人物IDなしの評価では人物リークを排除できず、未知人物への性能は未検証。",
        "",
        f"17種類のAU、{settings['sample_hz']}Hz、最大{settings['window_seconds']}秒の窓。MiniRocketMultivariate {settings['num_kernels']} kernels指定（84の倍数へ切り下げ）、RidgeClassifier。alphaは内側CVだけで選択。",
        "",
        "| Model | Accuracy mean ± SD | F1 mean ± SD | Balanced accuracy mean ± SD | ROC-AUC mean ± SD |",
        "|---|---|---|---|---|",
    ]
    for r in selected.itertuples():
        lines.append(
            f"| {r.model} | {r.accuracy_mean:.3f} ± {r.accuracy_std:.3f} | {r.f1_mean:.3f} ± {r.f1_std:.3f} | {r.balanced_accuracy_mean:.3f} ± {r.balanced_accuracy_std:.3f} | {r.roc_auc_mean:.3f} ± {r.roc_auc_std:.3f} |"
        )
    lines += [
        "",
        "標準偏差は外側fold間のばらつきであり、信頼区間やモデル差の有意性ではありません。単一seedの探索的実験であり、複数手法の比較後の最良値を独立した最終性能とは解釈しません。",
        "",
        "欠損区間は別の系列に分け、その前後を補間・畳み込みでつなぎません。短い窓を同じ長さにするため末尾のAU値を反復します。これは観測値の追加ではなく、モデル入力の補完です。窓特徴量は元の観測時間で重み付けして動画ごとに平均し、人工的な補完時間を動画の重みに加えません。窓間の順序は学習しません。",
        "",
        "短い区間の補完が結果に影響する可能性があります。各動画の窓数・補完割合はdata/processed/minirocket_sequences.csvで確認できます。",
        "",
        "MiniRocketの閾値、特徴量標準化、分類器は各訓練foldのみから学習します。内側CVでもMiniRocketを内側訓練だけでfitし直します。窓を独立サンプルとして学習・評価しません。分類スコアは確率ではありません。",
        "",
        f"![比較]({c['paths']['results']/'figures'/'minirocket_comparison.png'})",
        "",
        "[実装に使用したsktimeのMiniRocketMultivariate](https://www.sktime.net/en/stable/api_reference/auto_generated/sktime.transformations.panel.rocket.MiniRocketMultivariate.html) / [著者のMiniRocket実装](https://github.com/angus924/minirocket)",
    ]
    (c["root"] / "MINIROCKET_REPORT.md").write_text("\n".join(lines) + "\n")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(
        selected.model.to_numpy(),
        selected.balanced_accuracy_mean.to_numpy(),
        yerr=selected.balanced_accuracy_std.to_numpy(),
    )
    ax.set_ylim(0, 1)
    ax.set_ylabel("Balanced accuracy (outer-fold mean ± SD)")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(c["paths"]["results"] / "figures" / "minirocket_comparison.png")
    plt.close(fig)


def experiment(c):
    settings = c["minirocket"]
    df = pd.read_csv(c["paths"]["processed"] / "features_A.csv")
    stored = json.loads((c["paths"]["processed"] / "feature_settings.json").read_text())
    c = dict(c, **stored)
    columns = [x[:-5] + "_r" for x in df if x.endswith("_mean")]
    files = [c["paths"]["processed"] / f"{v}.csv" for v in df.video_id]
    videos = [
        make_sequence(pd.read_csv(file), columns, settings, c["max_gap_seconds"])
        for file in files
    ]
    folds, scope = read_partitions(df, c, save_name="minirocket.json")
    length = int(round(settings["sample_hz"] * settings["window_seconds"]))
    audit = []
    for vid, (ws, weights) in zip(df.video_id, videos):
        audit.append(
            dict(
                video_id=vid,
                windows=len(ws),
                observed_steps=sum(len(w) for w in ws),
                padded_steps=sum(length - len(w) for w in ws),
                duration_weighted_padding_fraction=float(
                    np.average([1 - len(w) / length for w in ws], weights=weights)
                ),
            )
        )
    pd.DataFrame(audit).to_csv(
        c["paths"]["processed"] / "minirocket_sequences.csv", index=False
    )
    y = df.label.to_numpy(dtype=int)
    rows = []
    predictions = []
    for fold, (tr, te, inner) in enumerate(folds):
        print(f"MiniRocket: outer fold {fold+1}/{len(folds)}", flush=True)
        train = [videos[i] for i in tr]
        alpha, search = select(train, y[tr], inner, settings, c["seed"])
        model = VideoMiniRocket(settings, c["seed"]).fit(train, y[tr], alpha)
        test = [videos[i] for i in te]
        score = model.decision_function(test)
        pred = model.predict(test)
        rows.append(
            dict(
                model="MiniRocket",
                feature_set="minirocket",
                fold=fold,
                **metrics(y[te], pred, score),
            )
        )
        predictions.extend(
            dict(
                model="MiniRocket",
                feature_set="minirocket",
                fold=fold,
                video_id=df.video_id.iloc[i],
                label=int(y[i]),
                prediction=int(p),
                score=float(s),
            )
            for i, p, s in zip(te, pred, score)
        )
        save_json(
            c["paths"]["results"] / "metrics" / f"MiniRocket_{fold}_search.json", search
        )
        save_model(
            c["paths"]["models"] / f"MiniRocket_fold_{fold}.joblib",
            model,
            columns,
            c,
            scope,
            df.video_id.iloc[tr],
        )
        pd.DataFrame(rows).to_csv(
            c["paths"]["results"] / "metrics" / "folds_minirocket.csv", index=False
        )
        pd.DataFrame(predictions).to_csv(
            c["paths"]["results"] / "metrics" / "predictions_minirocket.csv",
            index=False,
        )
        print(
            f'  alpha={alpha}; balanced accuracy={rows[-1]["balanced_accuracy"]:.3f}',
            flush=True,
        )
    groups = df.person_id.astype(str).to_numpy() if df.person_id.notna().all() else None
    inner = splits(y, groups, c["inner_folds"], c["seed"])
    alpha, search = select(videos, y, inner, settings, c["seed"])
    model = VideoMiniRocket(settings, c["seed"]).fit(videos, y, alpha)
    save_model(
        c["paths"]["models"] / "MiniRocket.joblib",
        model,
        columns,
        c,
        scope,
        df.video_id,
    )
    save_json(
        c["paths"]["results"] / "metrics" / "MiniRocket_final_search.json", search
    )
    summary = (
        pd.DataFrame(rows)
        .groupby(["model", "feature_set"])[
            ["accuracy", "precision", "recall", "f1", "balanced_accuracy", "roc_auc"]
        ]
        .agg(["mean", "std"])
    )
    summary.columns = ["_".join(x) for x in summary.columns]
    summary = summary.reset_index()
    baseline = c["paths"]["results"] / "tables" / "comparison_temporal.csv"
    if not baseline.exists():
        baseline = c["paths"]["results"] / "tables" / "comparison.csv"
    comparison = pd.concat([pd.read_csv(baseline), summary], ignore_index=True)
    comparison.to_csv(
        c["paths"]["results"] / "tables" / "comparison_minirocket.csv", index=False
    )
    plots(pd.DataFrame(predictions), "minirocket", c)
    write_report(comparison, c, len(df), scope, settings, folds)
    save_json(
        c["paths"]["results"] / "metrics" / "minirocket_provenance.json",
        dict(
            settings=settings,
            preprocessing=stored,
            seed=c["seed"],
            scope=scope,
            versions={
                n: importlib.metadata.version(n)
                for n in ("sktime", "numba", "scikit-learn", "numpy")
            },
            sequence_sha256={
                p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in files
            },
            split_sha256=hashlib.sha256(
                (c["paths"]["splits"] / "minirocket.json").read_bytes()
            ).hexdigest(),
            source_sha256={
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__), Path(__file__).with_name("sequence_data.py"))
            },
        ),
    )
    print(summary.to_string(index=False), flush=True)
    return summary


def main():
    a = parser(__doc__).parse_args()
    # Use the canonical module so saved classes load from other CLI entry points.
    from .minirocket import experiment as run_experiment

    run_experiment(config(a.config))


if __name__ == "__main__":
    main()
