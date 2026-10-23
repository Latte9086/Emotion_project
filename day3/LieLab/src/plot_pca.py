"""Descriptive PCA of the real cohort; does not retrain or evaluate a classifier."""
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from .common import config


def main():
    c = config()
    artifact = joblib.load(c['paths']['models'] / 'C_SVM.joblib')
    df = pd.read_csv(c['paths']['processed'] / 'features_C.csv')
    # Reuse the final model's exact fitted preprocessing and input column order.
    x = artifact['pipeline'][:-1].transform(df[artifact['columns']])
    pca = PCA(n_components=2, svd_solver='full')
    z = pca.fit_transform(x)
    variance = pca.explained_variance_ratio_ * 100
    fig, ax = plt.subplots(figsize=(9, 6.5))
    fig.patch.set_facecolor('#fbfaf6')
    ax.set_facecolor('#fbfaf6')
    for label, color, marker, name in [(0, '#368578', 'o', 'Truth'), (1, '#d65c6f', 'X', 'Lie')]:
        selected = df.label.to_numpy() == label
        ax.scatter(z[selected, 0], z[selected, 1], c=color, marker=marker,
                   s=78, alpha=.8, linewidths=.6, edgecolors='white',
                   label=f'{name} (n={selected.sum()})')
    ax.axhline(0, color='#bbb', lw=.6, zorder=0)
    ax.axvline(0, color='#bbb', lw=.6, zorder=0)
    ax.set_xlabel(f'Principal component 1 ({variance[0]:.1f}% of variance)')
    ax.set_ylabel(f'Principal component 2 ({variance[1]:.1f}% of variance)')
    ax.set_title('110 videos: 153 AU summary features projected into 2D', pad=18)
    ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.text(.5, .02, f'PCA retains {variance.sum():.1f}% of feature variance. Labels are for coloring only.\nDescriptive full-cohort visualization; not the SVM decision boundary or a performance evaluation.', ha='center', fontsize=9, color='#666')
    fig.tight_layout(rect=[0, .09, 1, 1])
    out = c['paths']['results'] / 'figures' / 'pca_C_features.png'
    fig.savefig(out, dpi=170)
    plt.close(fig)
    data = df[['video_id', 'label']].copy()
    data['PC1'], data['PC2'] = z[:, 0], z[:, 1]
    data.to_csv(c['paths']['results'] / 'tables' / 'pca_C_features.csv', index=False)
    assert np.isfinite(z).all() and len(z) == 110
    print(out)
    print('explained variance percent:', variance, 'total:', variance.sum())


if __name__ == '__main__':
    main()
