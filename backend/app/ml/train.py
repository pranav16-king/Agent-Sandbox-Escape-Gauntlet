"""
Training script for sandboxX ML Security Classifier.
Trains an ensemble pipeline for real-time 3-tier classification:
  0: ALLOW
  1: ASK
  2: BLOCK
Outputs:
  - backend/app/ml/model.joblib
  - backend/app/ml/metrics.json
"""

import os
import json
import time
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

from backend.app.ml.dataset import SECURITY_TRAINING_DATA

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"
METRICS_PATH = BASE_DIR / "metrics.json"

def build_training_pipeline() -> Pipeline:
    """
    Constructs a multi-scale n-gram text classification pipeline.
    Uses both word n-grams (1-2) and character n-grams (3-5) to capture
    both semantic terms (override, sudo, curl) and sub-word obfuscations.
    """
    feature_union = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            analyzer="word",
            sublinear_tf=True,
            min_df=1
        )),
        ("char_tfidf", TfidfVectorizer(
            ngram_range=(3, 5),
            analyzer="char_wb",
            sublinear_tf=True,
            min_df=1
        ))
    ])

    base_estimator = LogisticRegression(
        C=5.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42
    )

    pipeline = Pipeline([
        ("features", feature_union),
        ("classifier", base_estimator)
    ])

    return pipeline

def train_and_evaluate():
    start_time = time.time()
    print("=" * 60)
    print("sandboxX Security ML Classifier: Training Pipeline")
    print("=" * 60)

    # 1. Prepare data
    texts = [item[0] for item in SECURITY_TRAINING_DATA]
    labels = [item[1] for item in SECURITY_TRAINING_DATA]

    print(f"Total samples: {len(texts)}")
    print(f"Class distribution: ALLOW(0)={labels.count(0)}, ASK(1)={labels.count(1)}, BLOCK(2)={labels.count(2)}")

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels
    )

    # 2. Build and fit pipeline
    pipeline = build_training_pipeline()
    pipeline.fit(X_train, y_train)

    # 3. Evaluate on test set
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))

    print("\n--- Model Evaluation Report ---")
    print(f"Test Accuracy: {acc * 100:.2f}%")
    print(f"Macro F1 Score: {macro_f1:.4f}")
    print(f"Weighted F1 Score: {weighted_f1:.4f}")
    print("\nDetailed Classification Report:")
    target_names = ["ALLOW", "ASK", "BLOCK"]
    print(classification_report(y_test, y_pred, target_names=target_names))

    # 4. Fit on 100% of the dataset for maximum production coverage
    print("Refitting on 100% dataset for production deployment...")
    final_pipeline = build_training_pipeline()
    final_pipeline.fit(texts, labels)

    train_duration = round(time.time() - start_time, 3)

    # 5. Save model artifacts
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, MODEL_PATH)
    print(f"Saved model artifact: {MODEL_PATH}")

    metrics = {
        "model_name": "sandboxX-Security-Classifier-v1",
        "training_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_samples": len(texts),
        "test_samples": len(X_test),
        "test_accuracy": acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "classes": {
            "0": "ALLOW",
            "1": "ASK",
            "2": "BLOCK"
        },
        "training_time_sec": train_duration,
        "classes_count": {
            "ALLOW": labels.count(0),
            "ASK": labels.count(1),
            "BLOCK": labels.count(2)
        }
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics metadata: {METRICS_PATH}")
    print(f"Training successfully completed in {train_duration}s.")
    print("=" * 60)
    return metrics

if __name__ == "__main__":
    train_and_evaluate()
