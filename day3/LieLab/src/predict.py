"""Classify a new video with the saved feature schema and quality thresholds."""

import hashlib
import joblib
import pandas as pd
from pathlib import Path
from .common import config, parser
from .extract_au import extract
from .preprocess import clean
from .build_features import features


def predict(video, model, c):
    if model.suffix == ".pt":
        from .temporal import predict_video

        return predict_video(video, model, c)
    artifact = joblib.load(model)
    if artifact.get("model_type") == "minirocket":
        from .minirocket import predict_video

        return predict_video(video, artifact, c)
    c = dict(c, **artifact["preprocessing"])
    with video.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    vid = "prediction_" + digest[:16]
    csv = extract(video, vid, c)
    df, quality = clean(csv, c)
    if not quality["accepted"]:
        return {"prediction": None, "reason": quality["reason"], "quality": quality}
    vals = features(df, c, artifact["feature_set"])
    absent = set(artifact["columns"]) - set(vals)
    if absent:
        return {
            "prediction": None,
            "reason": "Missing required AU features: " + ",".join(sorted(absent)),
        }
    X = pd.DataFrame([vals])[artifact["columns"]]
    pipe = artifact["pipeline"]
    label = int(pipe.predict(X)[0])
    result = {
        "prediction": "Lie" if label else "Truth",
        "score_type": artifact["score_type"],
        "evaluation_scope": artifact["evaluation_scope"],
        "quality": quality,
    }
    if hasattr(pipe, "predict_proba"):
        scores = pipe.predict_proba(X)[0]
        result.update(
            lie_score=float(scores[1]), truth_score=float(scores[0]), calibrated=False
        )
    else:
        result["lie_decision_score"] = float(pipe.decision_function(X)[0])
        result["calibrated"] = False
    return result


def main():
    p = parser(__doc__)
    p.add_argument("--video", required=True)
    p.add_argument("--model")
    a = p.parse_args()
    c = config(a.config)
    import json

    model = (
        c["root"] / a.model
        if a.model
        else c["paths"]["models"] / "C_LogisticRegression.joblib"
    )
    print(json.dumps(predict(Path(a.video).resolve(), model, c), indent=2))


if __name__ == "__main__":
    main()
