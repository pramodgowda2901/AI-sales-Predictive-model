"""
SageMaker Training Job script for AI Sales Predictive Management.

Loads deal + signal data from S3 (Parquet), engineers features, trains
XGBoost and LightGBM models, selects the best by F1 on the validation
split, and saves the winning model to SM_MODEL_DIR.

SageMaker injects the following environment variables:
  SM_CHANNEL_TRAIN       – path to training Parquet files
  SM_CHANNEL_VALIDATION  – path to validation Parquet files
  SM_MODEL_DIR           – where to write the saved model artifact
  SM_OUTPUT_DATA_DIR     – where to write any extra output files
"""

import os
import json
import logging
import pickle
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
import xgboost as xgb
import lightgbm as lgb

from features import (
    FeaturePipeline,
    compute_deal_age,
    compute_stage_velocity,
    compute_rolling_engagement as compute_engagement_score,
    compute_historical_close_rate,
    FEATURE_COLS as PIPELINE_FEATURE_COLS,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SageMaker channel paths (injected by the training container)
# ---------------------------------------------------------------------------
TRAIN_DIR = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")
VAL_DIR = os.environ.get("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation")
MODEL_DIR = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
OUTPUT_DIR = os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data")

# ---------------------------------------------------------------------------
# Feature column names produced by feature engineering
# ---------------------------------------------------------------------------
# The canonical list lives in features.py (PIPELINE_FEATURE_COLS).
# We keep the original four-column list here for backward compatibility with
# the model training / evaluation code that was written before the pipeline
# module existed.
FEATURE_COLS = [
    "deal_age",
    "stage_velocity",
    "engagement_score",
    "historical_close_rate",
]
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
# Feature engineering  (helpers imported from features.py)
# ---------------------------------------------------------------------------

def build_close_rates(df: pd.DataFrame) -> dict:
    """
    Compute per-stage close rate from the training DataFrame.

    Delegates to FeaturePipeline._build_close_rates so the logic is defined
    in one place.
    """
    return FeaturePipeline._build_close_rates(df)


def engineer_features(
    df: pd.DataFrame, close_rates: dict
) -> pd.DataFrame:
    """Return a DataFrame with exactly the four engineered feature columns.

    Delegates to the helpers imported from features.py so that train.py and
    the inference container share identical feature computation logic.
    """
    features = pd.DataFrame(index=df.index)
    features["deal_age"] = compute_deal_age(df)
    features["stage_velocity"] = compute_stage_velocity(df)
    features["engagement_score"] = compute_engagement_score(df)
    features["historical_close_rate"] = compute_historical_close_rate(df, close_rates)
    return features


# ---------------------------------------------------------------------------
# Model training helpers
# ---------------------------------------------------------------------------

def train_xgboost(X_train: np.ndarray, y_train: np.ndarray) -> xgb.XGBClassifier:
    """Train an XGBoost binary classifier."""
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    logger.info("XGBoost training complete")
    return model


def train_lightgbm(X_train: np.ndarray, y_train: np.ndarray) -> lgb.LGBMClassifier:
    """Train a LightGBM binary classifier."""
    model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    logger.info("LightGBM training complete")
    return model


def evaluate_model(model, X_val: np.ndarray, y_val: np.ndarray, name: str) -> dict:
    """Return a metrics dict for the given model on the validation set."""
    y_pred = model.predict(X_val)
    metrics = {
        "model": name,
        "f1": float(f1_score(y_val, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_val, y_pred)),
        "precision": float(precision_score(y_val, y_pred, zero_division=0)),
        "recall": float(recall_score(y_val, y_pred, zero_division=0)),
    }
    logger.info(
        "%s — F1: %.4f  Accuracy: %.4f  Precision: %.4f  Recall: %.4f",
        name,
        metrics["f1"],
        metrics["accuracy"],
        metrics["precision"],
        metrics["recall"],
    )
    return metrics


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save_model(model, model_dir: str, model_name: str) -> str:
    """Pickle the model to *model_dir* and return the file path."""
    Path(model_dir).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(model_dir, f"{model_name}.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("Saved model to %s", out_path)
    return out_path


def save_metadata(
    metrics: dict,
    close_rates: dict,
    feature_cols: list,
    output_dir: str,
) -> None:
    """Write training metadata (metrics + close rates + feature list) to JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_cols": feature_cols,
        "close_rates": close_rates,
        "best_model_metrics": metrics,
    }
    out_path = os.path.join(output_dir, "training_metadata.json")
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved training metadata to %s", out_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== SageMaker Training Job started ===")
    logger.info("TRAIN_DIR=%s  VAL_DIR=%s  MODEL_DIR=%s", TRAIN_DIR, VAL_DIR, MODEL_DIR)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    train_df = load_parquet_dir(TRAIN_DIR)
    val_df = load_parquet_dir(VAL_DIR)

    if TARGET_COL not in train_df.columns:
        raise ValueError(
            f"Target column '{TARGET_COL}' not found in training data. "
            f"Available columns: {list(train_df.columns)}"
        )

    # ------------------------------------------------------------------
    # 2. Compute per-stage close rates from training data only
    # ------------------------------------------------------------------
    close_rates = build_close_rates(train_df)

    # ------------------------------------------------------------------
    # 3. Engineer features
    # ------------------------------------------------------------------
    X_train = engineer_features(train_df, close_rates)[FEATURE_COLS].values
    y_train = train_df[TARGET_COL].astype(int).values

    X_val = engineer_features(val_df, close_rates)[FEATURE_COLS].values
    y_val = val_df[TARGET_COL].astype(int).values

    logger.info(
        "Feature matrix shapes — train: %s  val: %s", X_train.shape, X_val.shape
    )

    # ------------------------------------------------------------------
    # 4. Train both models
    # ------------------------------------------------------------------
    xgb_model = train_xgboost(X_train, y_train)
    lgb_model = train_lightgbm(X_train, y_train)

    # ------------------------------------------------------------------
    # 5. Evaluate on validation split
    # ------------------------------------------------------------------
    xgb_metrics = evaluate_model(xgb_model, X_val, y_val, "xgboost")
    lgb_metrics = evaluate_model(lgb_model, X_val, y_val, "lightgbm")

    # ------------------------------------------------------------------
    # 6. Select best model by F1
    # ------------------------------------------------------------------
    if xgb_metrics["f1"] >= lgb_metrics["f1"]:
        best_model = xgb_model
        best_metrics = xgb_metrics
        best_name = "xgboost"
        logger.info("Best model: XGBoost (F1=%.4f)", best_metrics["f1"])
    else:
        best_model = lgb_model
        best_metrics = lgb_metrics
        best_name = "lightgbm"
        logger.info("Best model: LightGBM (F1=%.4f)", best_metrics["f1"])

    # ------------------------------------------------------------------
    # 7. Save best model + metadata
    # ------------------------------------------------------------------
    save_model(best_model, MODEL_DIR, best_name)

    # Also persist close_rates alongside the model so the inference
    # container can reconstruct the historical_close_rate feature.
    close_rates_path = os.path.join(MODEL_DIR, "close_rates.json")
    with open(close_rates_path, "w") as f:
        json.dump(close_rates, f)
    logger.info("Saved close rates to %s", close_rates_path)

    save_metadata(best_metrics, close_rates, FEATURE_COLS, OUTPUT_DIR)

    logger.info("=== Training job complete. Best model: %s ===", best_name)


if __name__ == "__main__":
    main()
