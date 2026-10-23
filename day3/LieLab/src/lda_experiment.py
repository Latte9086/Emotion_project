"""Shrinkage LDA: descriptive full-cohort plot and fixed-parameter held-out evaluation."""
import hashlib
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .common import config, save_json
from .evaluate import metrics, plots
from .sequence_data import read_partitions
import matplotlib.pyplot as plt


def new_model():
    # 153 dimensions > 88 training videos; shrinkage stabilizes the covariance.
    return make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True),
                         StandardScaler(),
                         LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto'))


def main():
    c = config()
    source = c['paths']['processed']/'features_C.csv'
    df = pd.read_csv(source)
    baseline = joblib.load(c['paths']['models']/'C_SVM.joblib')
    columns = baseline['columns']
    X, y = df[columns], df.label.to_numpy(dtype=int)
    folds, scope = read_partitions(df, c, save_name='lda.json')
    records, predictions = [], []
    for fold, (train, test, _) in enumerate(folds):
        model = new_model().fit(X.iloc[train], y[train])
        score = model.decision_function(X.iloc[test])
        pred = model.predict(X.iloc[test])
        records.append(dict(fold=fold, **metrics(y[test], pred, score)))
        predictions.extend(dict(model='LDA', fold=fold, video_id=df.video_id.iloc[i],
                                label=int(y[i]), prediction=int(p), score=float(s))
                           for i, p, s in zip(test, pred, score))
        joblib.dump(dict(pipeline=model, columns=columns, training_video_ids=df.video_id.iloc[train].tolist()),
                    c['paths']['models']/f'LDA_fold_{fold}.joblib')
    oof = pd.DataFrame(predictions)
    assert len(oof) == len(df) and oof.video_id.nunique() == len(df)
    full = new_model().fit(X, y)
    full_scores = full.decision_function(X)
    full_predictions = full.predict(X)
    artifact = dict(baseline, pipeline=full, model='LDA', score_type='decision_function')
    joblib.dump(artifact, c['paths']['models']/'C_LDA.joblib')
    pd.DataFrame(records).to_csv(c['paths']['results']/'metrics/folds_lda.csv', index=False)
    oof.to_csv(c['paths']['results']/'metrics/predictions_lda.csv', index=False)
    full_data = pd.DataFrame(dict(video_id=df.video_id, label=y, score=full_scores))
    full_data.to_csv(c['paths']['results']/'tables/lda_full_cohort_scores.csv', index=False)
    summary = pd.DataFrame(records).drop(columns='fold').agg(['mean', 'std'])
    summary.to_csv(c['paths']['results']/'tables/comparison_lda.csv')
    plots(oof, 'C', c)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    fig.patch.set_facecolor('#fbfaf6')
    for ax, data, title in zip(axes, [full_data, oof],
                              ['Fit and display the same 110 videos', 'Held-out videos only (5-fold CV)']):
        ax.set_facecolor('#fbfaf6')
        edges = np.linspace(data.score.min()-.1, data.score.max()+.1, 15)
        for label, color, name, marker in [(0, '#368578', 'Truth', 'o'), (1, '#d65c6f', 'Lie', 'x')]:
            scores = data.loc[data.label == label, 'score'].to_numpy()
            ax.hist(scores, bins=edges, alpha=.45, color=color, label=f'{name} (n={len(scores)})', edgecolor=color)
            ax.scatter(scores, np.full(len(scores), -.6 if label==0 else -1.3),
                       color=color, marker=marker, s=18, alpha=.7, clip_on=False)
        ax.axvline(0, color='#30234d', ls='--', lw=1.2, label='Decision boundary')
        ax.set_title(title, fontsize=12, pad=15)
        ax.set_xlabel('LDA decision score: negative = Truth, positive = Lie')
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(fontsize=9)
    axes[0].set_ylabel('Number of videos')
    fig.suptitle('LDA: separating Truth and Lie along one discriminant axis', fontsize=15)
    fig.text(.5, .015, 'Left: descriptive training fit, not generalization. Right: each video scored by a model that did not train on it.\nAxes have different ranges. Held-out scores pool five models; their scales may differ.', ha='center', fontsize=9, color='#666')
    fig.tight_layout(rect=[0, .1, 1, .94])
    fig.savefig(c['paths']['results']/'figures/lda_C_distribution.png', dpi=170)
    plt.close(fig)
    acc=summary.loc['mean','accuracy'];sd=summary.loc['std','accuracy']
    text = f'''# LDAの実データ実験

110動画・153種類の集計特徴量C。2クラスを1本の判別軸で分類します。

正解率（同じ外側5分割）: **{acc:.1%} ± {sd:.1%}**。SVMの69.1%と比較できますが、手法比較を重ねた探索的評価です。

| 指標 | 外側fold平均 | fold間SD |
|---|---:|---:|
'''
    for key in summary:
        text += f'| {key} | {summary.loc["mean",key]:.4f} | {summary.loc["std",key]:.4f} |\n'
    text += f'''
153特徴量に対し各foldの訓練動画は88本なので、共分散推定を安定させる縮小推定を用いました。scikit-learn LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")、設定は固定でハイパーパラメータ探索は行っていません。各fold内で欠損補完・標準化・共分散・判別方向を訓練動画だけから学習します。元のCと同じ外側分割を再利用しました。

![LDA分布]({c['paths']['results']/'figures/lda_C_distribution.png'})

左は全110本で学習し同じ110本を表示した図（学習時正解率{np.mean(full_predictions==y):.1%}）です。分離の見た目は未知データへの性能ではありません。右は各動画を学習に含まない外側テストの結果です。5つのモデルのスコアをまとめており尺度が異なる可能性があるため、ROC-AUCはfoldごとに計算しています。左右の横軸の範囲も異なります。

PCAはラベルを使わず、ばらつきが大きい方向を探します。LDAは訓練ラベルを使い、クラス間の分離とクラス内のまとまりから判別方向を探します。2クラスでは1軸です。この図はSVMの境界を描いたものではありません。

人物IDがなく人物リークは未解決です。嘘そのものの証明や未知人物への性能は示していません。LDAの確率出力も未較正です。

保存モデル: models/C_LDA.joblib。既存のsrc.predictから指定して利用可能。サイトの選択肢は変更していません。
'''
    (c['root']/'LDA_REPORT.md').write_text(text)
    save_json(c['paths']['results']/'metrics/lda_provenance.json', dict(
        scope=scope, solver='lsqr', shrinkage='auto', n_videos=len(df), columns=columns,
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print(summary.to_string())


if __name__ == '__main__':
    main()
