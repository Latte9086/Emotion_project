"""Descriptive AU analysis with person-aware inference and BH correction."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import ttest_ind, ttest_rel
from .common import config, parser


def bh(pvalues):
    p = np.array(pvalues, dtype=float)
    out = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    order = valid[np.argsort(p[valid])]
    if len(order):
        out[order] = np.minimum(
            1,
            np.minimum.accumulate(
                (p[order] * len(order) / np.arange(1, len(order) + 1))[::-1]
            )[::-1],
        )
    return out


def analyze(df, c):
    cols = [
        x
        for x in df
        if x.endswith("_mean") and "_delta_" not in x and "_derivative_" not in x
    ]
    groups = df.person_id.notna().all()
    partial = df.person_id.notna().any() and not groups
    data = (
        df.groupby(["person_id", "label"])[cols].mean().reset_index() if groups else df
    )
    mixed = (
        set(data.loc[data.label == 0, "person_id"])
        & set(data.loc[data.label == 1, "person_id"])
        if groups
        else set()
    )
    rows = []
    for col in cols:
        lie = data.loc[data.label == 1, col].dropna()
        truth = data.loc[data.label == 0, col].dropna()
        variance = (
            ((len(lie) - 1) * lie.var() + (len(truth) - 1) * truth.var())
            / (len(lie) + len(truth) - 2)
            if len(lie) + len(truth) > 2
            else np.nan
        )
        effect = (
            (lie.mean() - truth.mean()) / np.sqrt(variance) if variance > 0 else np.nan
        )
        p = np.nan
        method = "descriptive only: unresolved person dependence"
        if groups and mixed:
            pairs = data.pivot(index="person_id", columns="label", values=col).dropna()
            method = "paired person means (both-label persons only)"
            if len(pairs) >= 2:
                p = ttest_rel(pairs[1], pairs[0]).pvalue
        elif groups:
            method = "Welch test of independent person means"
            if min(len(lie), len(truth)) >= 2:
                p = ttest_ind(lie, truth, equal_var=False).pvalue
        rows.append(
            dict(
                au=col,
                lie_mean=lie.mean(),
                truth_mean=truth.mean(),
                mean_difference=lie.mean() - truth.mean(),
                cohens_d_descriptive=effect,
                p_value=p,
                method=method,
            )
        )
    result = pd.DataFrame(rows)
    result["q_bh"] = bh(result.p_value)
    result.to_csv(c["paths"]["results"] / "tables" / "au_comparison.csv", index=False)
    long = data.melt(
        id_vars=["label"], value_vars=cols, var_name="AU", value_name="intensity"
    )
    long["class"] = long.label.map({0: "Truth", 1: "Lie"})
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.barplot(data=long, x="AU", y="intensity", hue="class", errorbar=None, ax=ax)
    ax.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    fig.savefig(c["paths"]["results"] / "figures" / "au_means.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.boxplot(data=long, x="AU", y="intensity", hue="class", ax=ax)
    ax.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    fig.savefig(c["paths"]["results"] / "figures" / "au_boxplots.png")
    plt.close(fig)
    if "AU12_mean" in cols:
        fig, ax = plt.subplots()
        sns.violinplot(
            data=long[long.AU == "AU12_mean"], x="class", y="intensity", cut=0, ax=ax
        )
        fig.savefig(
            c["paths"]["results"] / "figures" / "au12_distribution.png",
            bbox_inches="tight",
        )
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(data[cols].corr(), vmin=-1, vmax=1, cmap="coolwarm", ax=ax)
    fig.tight_layout()
    fig.savefig(c["paths"]["results"] / "figures" / "au_correlation.png")
    plt.close(fig)
    for kind in "ABC":
        path = c["paths"]["results"] / "tables" / f"importance_{kind}.csv"
        if not path.exists():
            continue
        imp = (
            pd.read_csv(path)
            .groupby("feature")
            .importance.agg(["mean", "std"])
            .sort_values("mean")
            .tail(20)
        )
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.barh(imp.index, imp["mean"], xerr=imp["std"].fillna(0))
        ax.set_xlabel("Held-out permutation importance (balanced accuracy)")
        fig.tight_layout()
        fig.savefig(c["paths"]["results"] / "figures" / f"importance_{kind}.png")
        plt.close(fig)
    return result


def main():
    a = parser(__doc__).parse_args()
    c = config(a.config)
    analyze(pd.read_csv(c["paths"]["processed"] / "features_A.csv"), c)


if __name__ == "__main__":
    main()
