"""Create a factual experiment report from saved CSVs; no synthetic numbers."""

from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import platform
import subprocess
from pathlib import Path
import importlib.metadata
import pandas as pd
from .common import config, parser, save_json


def report(c):
    meta = pd.read_csv(c["paths"]["metadata"] / "videos.csv")
    extraction = pd.read_csv(c["paths"]["metadata"] / "extraction.csv")
    quality = pd.read_csv(c["paths"]["metadata"] / "quality.csv")
    comparison = pd.read_csv(c["paths"]["results"] / "tables" / "comparison.csv")
    ids = quality.loc[quality.accepted == True, "video_id"]
    accepted = meta[meta.video_id.isin(ids) & meta.label.notna()]
    settings = json.loads(
        (c["paths"]["processed"] / "feature_settings.json").read_text()
    )
    split = json.loads((c["paths"]["splits"] / "A.json").read_text())
    scope = (
        "本実験は確認済み人物IDがないため、動画単位の暫定評価です。人物リークを排除した未知人物への汎化性能は未検証です。"
        if accepted.person_id.isna().any()
        else "確認済み人物IDを用いた人物単位の交差検証です。"
    )
    lines = [
        "# 実データ実験レポート",
        "",
        f"生成時刻（Asia/Tokyo）: {datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()}",
        "",
        f"データ: {len(meta)}動画。抽出成功 {int(extraction.success.sum())}/{len(extraction)}。品質通過・既知ラベル {len(accepted)}動画。",
        f"採用ラベル: Truth={int((accepted.label==0).sum())}, Lie={int((accepted.label==1).sum())}。",
        "",
        scope,
        f"外側{len(split['folds'])}fold / 内側{len(split['folds'][0]['inner'])}fold。confidence≥{settings['confidence']}、有効フレーム率≥{settings['valid_ratio']}、seed={c['seed']}。",
        "",
        "| Model | Features | Accuracy mean ± SD | F1 mean ± SD | Balanced accuracy mean ± SD | ROC-AUC mean ± SD |",
        "|---|---|---|---|---|---|",
    ]
    for r in comparison.itertuples():
        values = [
            f'{getattr(r,k+"_mean"):.3f} ± {getattr(r,k+"_std"):.3f}'
            for k in ("accuracy", "f1", "balanced_accuracy", "roc_auc")
        ]
        lines.append(f"| {r.model} | {r.feature_set} | " + " | ".join(values) + " |")
    lines += [
        "",
        "SDは外側fold間の標本標準偏差であり信頼区間ではありません。モデル間の差の有意性や実際の嘘の確率を示しません。最高性能の候補をこの表から選んだ場合、独立したデータでの確認が必要です。",
        "",
        "AU検定・重要度は results/tables/、グラフは results/figures/、再現手順と利用条件はREADME.mdを参照してください。ダミーデータの自動テスト結果はこの表に含みません。",
    ]
    auc = pd.read_csv(c["paths"]["results"] / "tables" / "au_comparison.csv")
    lines += [
        "",
        (
            "人物IDのない本実験のAU群間比較は記述統計に限定し、p値・多重比較補正q値は計算していません。"
            if auc.p_value.isna().all()
            else "AU群間比較の検定方法・対象集団はau_comparison.csvを参照してください。"
        ),
    ]
    importance = pd.read_csv(c["paths"]["results"] / "tables" / "importance_C.csv")
    top = (
        importance.groupby("feature")
        .importance.agg(["mean", "std"])
        .sort_values("mean", ascending=False)
        .head(5)
    )
    lines += [
        "",
        "CのRandom Forest: 外側テストデータでのPermutation Importance上位（Balanced Accuracyの低下量）",
        "",
        "| Feature | Mean | Fold SD |",
        "|---|---|---|",
    ]
    for feature, row in top.iterrows():
        lines.append(f"| {feature} | {row['mean']:.4f} | {row['std']:.4f} |")
    lines += [
        "",
        "相関した特徴への寄与は分散する場合があります。重要度は嘘を生む表情の因果的証拠ではありません。",
        "",
        f"![モデル比較]({c['paths']['results'] / 'figures' / 'performance.png'})",
        "",
        "実装の自動テスト15件（ダミーデータ）の検証範囲は [TEST_REPORT.md](TEST_REPORT.md) を参照してください。",
    ]
    smoke = c["paths"]["results"] / "metrics" / "prediction_smoke.json"
    if smoke.exists():
        prediction = json.loads(smoke.read_text())
        if prediction.get("prediction") is not None:
            q = prediction["quality"]
            lines += [
                "",
                f"学習に使っていない付属動画による予測CLIの動作確認は成功（有効{q['valid_frames']}/{q['total_frames']}フレーム）。正解ラベルがないため予測精度の評価には使用していません。",
            ]
    path = c["root"] / "EXPERIMENT_REPORT.md"
    path.write_text("\n".join(lines) + "\n")
    versions = {
        name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "scikit-learn", "scipy", "matplotlib", "joblib")
    }
    inputs = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            c["paths"]["metadata"] / "videos.csv",
            c["paths"]["metadata"] / "quality.csv",
            *sorted(c["paths"]["processed"].glob("features_*.csv")),
        ]
    }
    binary = c["openface_binary"]
    binary_sha256 = None
    if binary.is_file():
        with binary.open("rb") as f:
            binary_sha256 = hashlib.file_digest(f, "sha256").hexdigest()
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=binary.parent,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    archive = c["paths"]["raw"] / "dataset.zip"
    archive_hash = None
    if archive.exists():
        with archive.open("rb") as f:
            archive_hash = hashlib.file_digest(f, "sha256").hexdigest()
    save_json(
        c["paths"]["results"] / "metrics" / "provenance.json",
        dict(
            python=platform.python_version(),
            openface_binary_sha256=binary_sha256,
            repository_revision=revision,
            dataset_archive_sha256=archive_hash,
            evaluation_settings={
                k: c[k]
                for k in ("seed", "outer_folds", "inner_folds", "permutation_repeats")
            },
            source_sha256={
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).parent.glob("*.py")
            },
            packages=versions,
            input_sha256=inputs,
            feature_settings=json.loads(
                (c["paths"]["processed"] / "feature_settings.json").read_text()
            ),
        ),
    )
    print(path)
    return path


def main():
    a = parser(__doc__).parse_args()
    report(config(a.config))


if __name__ == "__main__":
    main()
