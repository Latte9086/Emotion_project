"""Metrics and figures from held-out outer-fold predictions."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    roc_auc_score,
    ConfusionMatrixDisplay,
    RocCurveDisplay,
)
from .common import config, parser


def metrics(y, pred, score):
    return dict(
        accuracy=accuracy_score(y, pred),
        precision=precision_score(y, pred, zero_division=0),
        recall=recall_score(y, pred, zero_division=0),
        f1=f1_score(y, pred, zero_division=0),
        balanced_accuracy=balanced_accuracy_score(y, pred),
        roc_auc=roc_auc_score(y, score) if len(set(y)) == 2 else None,
    )


def plots(predictions, kind, c):
    for name, df in predictions.groupby("model"):
        fig, ax = plt.subplots()
        ConfusionMatrixDisplay.from_predictions(
            df.label,
            df.prediction,
            labels=[0, 1],
            display_labels=["Truth", "Lie"],
            ax=ax,
        )
        fig.savefig(
            c["paths"]["results"] / "figures" / f"confusion_{kind}_{name}.png",
            bbox_inches="tight",
        )
        plt.close(fig)
        # Fold-specific curves: SVM decision scales need not agree across folds.
        fig, ax = plt.subplots()
        for fold, d in df.groupby("fold"):
            if d.label.nunique() == 2:
                RocCurveDisplay.from_predictions(
                    d.label, d.score, name=f"fold {fold}", ax=ax
                )
        ax.set_title(f"{name} / {kind}: outer folds")
        fig.savefig(
            c["paths"]["results"] / "figures" / f"roc_{kind}_{name}.png",
            bbox_inches="tight",
        )
        plt.close(fig)


def performance_plot(summary, c):
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, kind in enumerate("ABC"):
        d = summary[summary.feature_set == kind].sort_values("model")
        import numpy as np

        ax.bar(
            np.arange(len(d)) + (i - 1) * 0.25,
            d.balanced_accuracy_mean,
            width=0.25,
            yerr=d.balanced_accuracy_std,
            label=kind,
        )
    ax.set_xticks(range(len(d)), d.model, rotation=15)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Balanced accuracy (mean ± fold SD)")
    ax.legend()
    fig.savefig(
        c["paths"]["results"] / "figures" / "performance.png", bbox_inches="tight"
    )
    plt.close(fig)


def main():
    a = parser(__doc__).parse_args()
    c = config(a.config)
    for kind in "ABC":
        plots(
            pd.read_csv(c["paths"]["results"] / "metrics" / f"predictions_{kind}.csv"),
            kind,
            c,
        )
    performance_plot(
        pd.read_csv(c["paths"]["results"] / "tables" / "comparison.csv"), c
    )


if __name__ == "__main__":
    main()
