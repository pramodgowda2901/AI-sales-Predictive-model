"""
SageMaker Evaluation script for AI Sales Predictive Management.

Loads the trained model and FeaturePipeline from SM_MODEL_DIR, evaluates on
the held-out test set from SM_CHANNEL_TEST, and writes a performance report
JSON to S3.

SageMaker injects the following environment variables:
  SM_MODEL_DIR      – directory containing the saved model (.pkl) and pipeline.pkl
  SM_CHANNEL_TEST   – path to held-out test Parquet files

Additional environment variables (set via SageMaker container environment):
  S3_BUCKET         – destination S3 bucket for the performance report
  TENANT_ID         – tenant identifier
  MODEL_VERSION     – model version string (e.g. "v1.2.3")

Output S3 path:
  s3://{S3_BUCKET}/model-artifacts/tenants/{TENANT_ID}/reports/{MODEL_VERSION}.json
"""

import json
import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from features import FeaturePipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
MODEL_DIR = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
TEST_DIR = os.environ.get("SM_CHANNEL_TEST", "/opt/ml/input/data/test")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
TENANT_ID = os.environ.get("TENANT_ID", "")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "latest")

TARGET_COL = "won"  # binary: 1 = Closed Won, 0 = Closed Lost


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_parquet_dir(directory: str) -> pd.DataFrame:
    """Read all Parquet files in *directory* and concatenate into one DataFrame."""
    path = Path(directory)
    files = list(path.glob("*.parquet")) + list(path.glob("*.snappy.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files found in {directory}")
    frames = [pd.read_parquet(f) for f in sorted(files)]
    df = pd.concat(frames, ignore_index=True)
    logger.info("Loaded %d rows from %s (%d file(s))", len(df), directory, len(files))
    return df


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_dir: str):
    """
    Load the trained model from *model_dir*.

    Looks for any .pkl file that is not 'pipeline.pkl' (the FeaturePipeline).
    Raises FileNotFoundError if no model file is found.
    """
    model_dir_path = Path(model_dir)
    candidates = [
        p for p in model_dir_path.glob("*.pkl")
        if p.name != "pipeline.pkl"
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No model .pkl file found in {model_dir} "
            "(expected a file other than pipeline.pkl)"
        )
    preferred = ["xgboost.pkl", "lightgbm.pkl"]
    model_path = None
    for name in preferred:
        match = model_dir_path / name
        if match in candidates:
            model_path = match
            break
    if model_path is None:
        model_path = candidates[0]

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    logger.info("Loaded model from %s", model_path)
    return model


def load_pipeline(model_dir: str) -> FeaturePipeline:
    """Load the fitted FeaturePipeline from *model_dir*/pipeline.pkl."""
    pipeline_path = Path(model_dir) / "pipeline.pkl"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"pipeline.pkl not found in {model_dir}")
    pipeline = FeaturePipeline.load(str(pipeline_path))
    logger.info("Loaded FeaturePipeline from %s", pipeline_path)
    return pipeline


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model, X: pd.DataFrame, y) -> dict:
    """
    Compute accuracy, precision, recall, and F1 on the given feature matrix.

    Returns a dict with float values for each metric.
    """
    y_pred = model.predict(X.values)
    return {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
    }


# ---------------------------------------------------------------------------
# S3 report upload
# ---------------------------------------------------------------------------

def write_report_to_s3(report: dict, bucket: str, tenant_id: str, version: str) -> str:
    """
    Serialise *report* as JSON and upload to S3.

    S3 key: model-artifacts/tenants/{tenant_id}/reports/{version}.json

    Returns the full S3 URI of the uploaded object.
    """
    key = f"model-artifacts/tenants/{tenant_id}/reports/{version}.json"
    body = json.dumps(report, indent=2).encode("utf-8")

    s3_client = boto3.client("s3")
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    s3_uri = f"s3://{bucket}/{key}"
    logger.info("Performance report written to %s", s3_uri)
    return s3_uri


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== SageMaker Evaluation Job started ===")
    logger.info(
        "MODEL_DIR=%s  TEST_DIR=%s  TENANT_ID=%s  MODEL_VERSION=%s",
        MODEL_DIR, TEST_DIR, TENANT_ID, MODEL_VERSION,
    )

    if not S3_BUCKET:
        raise ValueError("S3_BUCKET environment variable must be set")
    if not TENANT_ID:
        raise ValueError("TENANT_ID environment variable must be set")

    # 1. Load model and feature pipeline
    model = load_model(MODEL_DIR)
    pipeline = load_pipeline(MODEL_DIR)

    # 2. Load held-out test data
    test_df = load_parquet_dir(TEST_DIR)

    if TARGET_COL not in test_df.columns:
        raise ValueError(
            f"Target column '{TARGET_COL}' not found in test data. "
            f"Available columns: {list(test_df.columns)}"
        )

    y_test = test_df[TARGET_COL].astype(int).values
    sample_count = len(test_df)
    logger.info("Test set: %d samples", sample_count)

    # 3. Transform features using the fitted pipeline
    X_test = pipeline.transform(test_df)
    logger.info("Feature matrix shape: %s", X_test.shape)

    # 4. Compute evaluation metrics
    metrics = evaluate(model, X_test, y_test)
    logger.info(
        "Metrics — Accuracy: %.4f  Precision: %.4f  Recall: %.4f  F1: %.4f",
        metrics["accuracy"],
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
    )

    # 5. Build performance report
    report = {
        "tenantId": TENANT_ID,
        "modelVersion": MODEL_VERSION,
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "sampleCount": sample_count,
    }

    # 6. Write report to S3
    s3_uri = write_report_to_s3(report, S3_BUCKET, TENANT_ID, MODEL_VERSION)
    logger.info("=== Evaluation complete. Report at: %s ===", s3_uri)


if __name__ == "__main__":
    main()
