"""Nested CV with training-only preprocessing and held-out permutation importance."""

import re
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from .common import config, parser, save_json
from .evaluate import metrics, plots


def splits(y, groups, requested, seed):
    y = np.asarray(y)
    maximum = min(requested, int(np.bincount(y, minlength=2).min()))
    if groups is not None:
        maximum = min(maximum, len(np.unique(groups)))
    for n in range(maximum, 1, -1):
        # Group stratification is heuristic: check actual partitions before accepting.
        for attempt in range(20 if groups is not None else 1):
            cv = (
                StratifiedGroupKFold(n, shuffle=True, random_state=seed + attempt)
                if groups is not None
                else StratifiedKFold(n, shuffle=True, random_state=seed)
            )
            partitions = list(cv.split(np.zeros(len(y)), y, groups))
            if all(
                len(np.unique(y[tr])) == 2 and len(np.unique(y[te])) == 2
                for tr, te in partitions
            ):
                if groups is not None:
                    assert all(
                        not set(np.asarray(groups)[tr]) & set(np.asarray(groups)[te])
                        for tr, te in partitions
                    )
                return partitions
    raise ValueError(
        "Insufficient class/group counts for two-class cross-validation; collect more labeled data"
    )


def nested_splits(y, groups, c):
    for n in range(c["outer_folds"], 1, -1):
        for offset in range(20 if groups is not None else 1):
            try:
                outer = splits(y, groups, n, c["seed"] + offset)
                inners = [
                    splits(
                        np.asarray(y)[tr],
                        None if groups is None else np.asarray(groups)[tr],
                        c["inner_folds"],
                        c["seed"],
                    )
                    for tr, _ in outer
                ]
                return outer, inners
            except ValueError:
                continue
    raise ValueError(
        "Insufficient independent class/group data for nested CV (outer and inner folds both require two classes)"
    )


def models(seed):
    return {
        "Dummy": (DummyClassifier(strategy="prior"), {}),
        "LogisticRegression": (
            LogisticRegression(max_iter=3000, random_state=seed),
            {"classifier__C": [0.1, 1, 10]},
        ),
        "SVM": (
            SVC(kernel="rbf", random_state=seed),
            {"classifier__C": [0.1, 1, 10], "classifier__gamma": ["scale", 0.01]},
        ),
        "RandomForest": (
            RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=1),
            {
                "classifier__max_depth": [None, 3],
                "classifier__min_samples_leaf": [1, 3],
            },
        ),
    }


def fit_search(model, grid, X, y, inner):
    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("classifier", clone(model)),
        ]
    )
    return GridSearchCV(
        pipe, grid, cv=inner, scoring="balanced_accuracy", n_jobs=1, error_score="raise"
    ).fit(X, y)


def train_set(df, kind, c):
    if df.video_id.duplicated().any():
        raise ValueError("Duplicate video IDs")
    if not df.label.isin([0, 1]).all():
        raise ValueError("Labels must be 0 or 1")
    if df.person_id.notna().any() and df.person_id.isna().any():
        raise ValueError(
            "Partially missing person IDs: complete verified IDs or explicitly remove all IDs for provisional video CV"
        )
    groups = df.person_id.astype(str).to_numpy() if df.person_id.notna().all() else None
    columns = [
        x
        for x in df
        if re.fullmatch(
            r"AU\d+_(mean|std|max|median|q75|delta_abs_mean|delta_std|active_time_fraction|derivative_abs_mean)",
            x,
        )
    ]
    if not columns:
        raise ValueError("No AU features")
    X = df[columns].replace([np.inf, -np.inf], np.nan)
    y = df.label.to_numpy(dtype=int)
    # Establish feasible inner partitions before producing evaluation results.
    outer, inner_all = nested_splits(y, groups, c)
    save_json(
        c["paths"]["splits"] / f"{kind}.json",
        {
            "scope": (
                "person" if groups is not None else "video (person leakage unresolved)"
            ),
            "folds": [
                {
                    "train": df.video_id.iloc[tr].tolist(),
                    "test": df.video_id.iloc[te].tolist(),
                    "inner": [
                        {
                            "train": df.video_id.iloc[tr[a]].tolist(),
                            "validation": df.video_id.iloc[tr[b]].tolist(),
                        }
                        for a, b in inner
                    ],
                }
                for (tr, te), inner in zip(outer, inner_all)
            ],
        },
    )
    scores = []
    predictions = []
    importance = []
    for name, (model, grid) in models(c["seed"]).items():
        for fold, ((tr, te), inner) in enumerate(zip(outer, inner_all)):
            search = fit_search(model, grid, X.iloc[tr], y[tr], inner)
            fitted = search.best_estimator_
            pred = fitted.predict(X.iloc[te])
            score = (
                fitted.predict_proba(X.iloc[te])[:, 1]
                if hasattr(fitted, "predict_proba")
                else fitted.decision_function(X.iloc[te])
            )
            scores.append(
                dict(
                    model=name,
                    feature_set=kind,
                    fold=fold,
                    **metrics(y[te], pred, score),
                )
            )
            for i, p, s in zip(te, pred, score):
                predictions.append(
                    dict(
                        model=name,
                        feature_set=kind,
                        fold=fold,
                        video_id=df.video_id.iloc[i],
                        label=int(y[i]),
                        prediction=int(p),
                        score=float(s),
                    )
                )
            save_json(
                c["paths"]["results"]
                / "metrics"
                / f"{kind}_{name}_{fold}_parameters.json",
                search.best_params_,
            )
            if name == "RandomForest":
                imp = permutation_importance(
                    fitted,
                    X.iloc[te],
                    y[te],
                    scoring="balanced_accuracy",
                    n_repeats=c["permutation_repeats"],
                    random_state=c["seed"],
                )
                importance.extend(
                    dict(
                        feature=x,
                        feature_set=kind,
                        fold=fold,
                        importance=float(v),
                        std=float(s),
                    )
                    for x, v, s in zip(
                        columns, imp.importances_mean, imp.importances_std
                    )
                )
        # Deployment refit is distinct from outer-fold performance estimation.
        full_inner = splits(y, groups, c["inner_folds"], c["seed"])
        final = fit_search(model, grid, X, y, full_inner)
        import sklearn, platform

        artifact = dict(
            python_version=platform.python_version(),
            sklearn_version=sklearn.__version__,
            pipeline=final.best_estimator_,
            columns=columns,
            feature_set=kind,
            preprocessing={
                k: c[k]
                for k in (
                    "confidence",
                    "valid_ratio",
                    "activation_threshold",
                    "max_gap_seconds",
                )
            },
            evaluation_scope="person" if groups is not None else "video",
            score_type=(
                "uncalibrated predict_proba" if name != "SVM" else "decision_function"
            ),
            model=name,
        )
        joblib.dump(artifact, c["paths"]["models"] / f"{kind}_{name}.joblib")
    pd.DataFrame(scores).to_csv(
        c["paths"]["results"] / "metrics" / f"folds_{kind}.csv", index=False
    )
    pd.DataFrame(predictions).to_csv(
        c["paths"]["results"] / "metrics" / f"predictions_{kind}.csv", index=False
    )
    pd.DataFrame(importance).to_csv(
        c["paths"]["results"] / "tables" / f"importance_{kind}.csv", index=False
    )
    plots(pd.DataFrame(predictions), kind, c)
    return pd.DataFrame(scores)


def main():
    a = parser(__doc__).parse_args()
    c = config(a.config)
    results = []
    import json

    c.update(
        json.loads((c["paths"]["processed"] / "feature_settings.json").read_text())
    )
    for kind in "ABC":
        print(f"Nested CV: feature set {kind}", flush=True)
        results.append(
            train_set(
                pd.read_csv(c["paths"]["processed"] / f"features_{kind}.csv"), kind, c
            )
        )
    all_scores = pd.concat(results, ignore_index=True)
    summary = all_scores.groupby(["model", "feature_set"])[
        ["accuracy", "precision", "recall", "f1", "balanced_accuracy", "roc_auc"]
    ].agg(["mean", "std"])
    summary.columns = ["_".join(x) for x in summary.columns]
    summary.to_csv(c["paths"]["results"] / "tables" / "comparison.csv")
    from .evaluate import performance_plot

    performance_plot(summary.reset_index(), c)
    print(summary)


if __name__ == "__main__":
    main()
