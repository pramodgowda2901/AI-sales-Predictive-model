"""
Feature engineering pipeline for AI Sales Predictive Management.

Provides a reusable FeaturePipeline class and save_to_s3 utility that can be
imported by both the SageMaker training script (train.py) and the inference
container.

Pipeline steps:
  1. Compute rolling 14-day engagement window (signal count)
  2. Encode categorical stage values (OrdinalEncoder)
  3. Normalize numeric features: deal_age, stage_velocity, engagement_score
     using StandardScaler
  4. Append historical_close_rate (pass-through, already numeric 0-1)

Output: a pandas DataFrame (feature matrix) with columns matching FEATURE_COLS.
"""

import io
import json
import logging
import pickle
from typing import Optional

import boto3
import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column names produced by the pipeline (order matters for model input)
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "deal_age",
    "stage_velocity",
    "engagement_score",
    "historical_close_rate",
    "stage_encoded",
]

# Numeric columns that are normalized with StandardScaler
NUMERIC_COLS = ["deal_age", "stage_velocity", "engagement_score"]

# Categorical columns encoded with OrdinalEncoder
CATEGORICAL_COLS = ["stage"]


# ---------------------------------------------------------------------------
# Low-level feature computation helpers (reused from train.py logic)
# ---------------------------------------------------------------------------

def compute_deal_age(df: pd.DataFrame) -> pd.Series:
    """Days between deal creation and reference date (close_date or now)."""
    now = pd.Timestamp.utcnow()
    created = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    if "close_date" in df.columns:
        ref = pd.to_datetime(df["close_date"], utc=True, errors="coerce").fillna(now)
    else:
        ref = now
    age = (ref - created).dt.days.clip(lower=0).fillna(0)
    return age.astype(float)


def compute_stage_velocity(df: pd.DataFrame) -> pd.Series:
    """
    Average days spent per stage transition.

    Expects a 'stage_transitions' column with a list of dicts:
      [{"stage": "Prospecting", "entered_at": "2024-01-01T00:00:00Z"}, ...]
    Falls back to 0 when absent or malformed.
    """
    if "stage_transitions" not in df.columns:
        return pd.Series(0.0, index=df.index)

    velocities = []
    for transitions in df["stage_transitions"]:
        if not transitions or not isinstance(transitions, list) or len(transitions) < 2:
            velocities.append(0.0)
            continue
        try:
            times = [pd.Timestamp(t["entered_at"], tz="UTC") for t in transitions]
            deltas = [(times[i + 1] - times[i]).days for i in range(len(times) - 1)]
            velocities.append(float(np.mean(deltas)) if deltas else 0.0)
        except (KeyError, TypeError, ValueError):
            velocities.append(0.0)
    return pd.Series(velocities, index=df.index, dtype=float)


def compute_rolling_engagement(df: pd.DataFrame, window_days: int = 14) -> pd.Series:
    """
    Count of signals recorded for each deal within the last *window_days* days.

    Expects a 'signals' column with a list of dicts containing 'ingested_at'.
    Falls back to 0 when absent or malformed.
    """
    if "signals" not in df.columns:
        return pd.Series(0.0, index=df.index)

    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=window_days)
    scores = []
    for signals in df["signals"]:
        if not signals or not isinstance(signals, list):
            scores.append(0.0)
            continue
        count = 0
        for s in signals:
            try:
                ts = pd.Timestamp(s["ingested_at"], tz="UTC")
                if ts >= cutoff:
                    count += 1
            except (KeyError, TypeError, ValueError):
                pass
        scores.append(float(count))
    return pd.Series(scores, index=df.index, dtype=float)


def compute_historical_close_rate(
    df: pd.DataFrame, close_rates: dict
) -> pd.Series:
    """
    Per-stage historical close rate.

    *close_rates* maps stage name → float (0–1).
    Deals whose stage is not in the map receive the global mean.
    """
    global_mean = float(np.mean(list(close_rates.values()))) if close_rates else 0.5
    return df["stage"].map(close_rates).fillna(global_mean).astype(float)


# ---------------------------------------------------------------------------
# FeaturePipeline
# ---------------------------------------------------------------------------

class FeaturePipeline:
    """
    Stateful feature engineering pipeline.

    Usage (training):
        pipeline = FeaturePipeline()
        X = pipeline.fit_transform(train_df, close_rates=close_rates)

    Usage (inference):
        pipeline = FeaturePipeline.load(path)
        X = pipeline.transform(inference_df)

    The pipeline:
      1. Computes raw features (deal_age, stage_velocity, engagement_score,
         historical_close_rate) from the input DataFrame.
      2. Encodes the categorical 'stage' column with OrdinalEncoder (fitted on
         training data; unknown categories at inference time map to -1).
      3. Normalises deal_age, stage_velocity, and engagement_score with
         StandardScaler (fitted on training data).
    """

    def __init__(self, engagement_window_days: int = 14) -> None:
        self.engagement_window_days = engagement_window_days
        self._scaler: Optional[StandardScaler] = None
        self._encoder: Optional[OrdinalEncoder] = None
        self._close_rates: dict = {}
        self._fitted: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_transform(
        self, df: pd.DataFrame, close_rates: Optional[dict] = None
    ) -> pd.DataFrame:
        """
        Fit the pipeline on *df* and return the transformed feature matrix.

        Parameters
        ----------
        df : pd.DataFrame
            Raw deal + signal DataFrame (training split).
        close_rates : dict, optional
            Pre-computed per-stage close rates.  When None the pipeline
            computes them from *df* (requires a 'won' column).

        Returns
        -------
        pd.DataFrame
            Feature matrix with columns defined by FEATURE_COLS.
        """
        if close_rates is not None:
            self._close_rates = close_rates
        else:
            self._close_rates = self._build_close_rates(df)

        raw = self._compute_raw_features(df)

        # Fit + transform stage encoder
        self._encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1, dtype=float
        )
        raw["stage_encoded"] = self._encoder.fit_transform(
            df[["stage"]].fillna("Unknown")
        ).ravel()

        # Fit + transform numeric scaler
        self._scaler = StandardScaler()
        raw[NUMERIC_COLS] = self._scaler.fit_transform(raw[NUMERIC_COLS])

        self._fitted = True
        logger.info(
            "FeaturePipeline fitted on %d rows; stages=%d",
            len(df),
            len(self._encoder.categories_[0]),
        )
        return raw[FEATURE_COLS].reset_index(drop=True)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the fitted pipeline to *df* (inference / validation).

        Parameters
        ----------
        df : pd.DataFrame
            Raw deal + signal DataFrame.

        Returns
        -------
        pd.DataFrame
            Feature matrix with columns defined by FEATURE_COLS.

        Raises
        ------
        RuntimeError
            If the pipeline has not been fitted yet.
        """
        if not self._fitted:
            raise RuntimeError(
                "FeaturePipeline must be fitted before calling transform(). "
                "Call fit_transform() first."
            )

        raw = self._compute_raw_features(df)

        raw["stage_encoded"] = self._encoder.transform(
            df[["stage"]].fillna("Unknown")
        ).ravel()

        raw[NUMERIC_COLS] = self._scaler.transform(raw[NUMERIC_COLS])

        return raw[FEATURE_COLS].reset_index(drop=True)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Pickle the fitted pipeline to *path*."""
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("FeaturePipeline saved to %s", path)

    @classmethod
    def load(cls, path: str) -> "FeaturePipeline":
        """Load a previously saved pipeline from *path*."""
        with open(path, "rb") as f:
            pipeline = pickle.load(f)
        if not isinstance(pipeline, cls):
            raise TypeError(f"Expected FeaturePipeline, got {type(pipeline)}")
        logger.info("FeaturePipeline loaded from %s", path)
        return pipeline

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_raw_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute raw (un-scaled, un-encoded) feature columns."""
        features = pd.DataFrame(index=df.index)
        features["deal_age"] = compute_deal_age(df)
        features["stage_velocity"] = compute_stage_velocity(df)
        features["engagement_score"] = compute_rolling_engagement(
            df, window_days=self.engagement_window_days
        )
        features["historical_close_rate"] = compute_historical_close_rate(
            df, self._close_rates
        )
        return features

    @staticmethod
    def _build_close_rates(df: pd.DataFrame) -> dict:
        """Compute per-stage close rate from *df* (requires 'stage' and 'won' columns)."""
        if "stage" not in df.columns or "won" not in df.columns:
            logger.warning(
                "Cannot compute close rates: 'stage' or 'won' column missing. "
                "Using empty dict."
            )
            return {}
        grouped = df.groupby("stage")["won"]
        rates = (grouped.sum() / grouped.count()).to_dict()
        logger.info("Computed close rates for %d stages", len(rates))
        return rates


# ---------------------------------------------------------------------------
# S3 output helper
# ---------------------------------------------------------------------------

def save_to_s3(
    feature_matrix: pd.DataFrame,
    s3_uri: str,
    tenant_id: str,
    boto_session: Optional[boto3.Session] = None,
) -> str:
    """
    Write *feature_matrix* as a Parquet file to *s3_uri*.

    Parameters
    ----------
    feature_matrix : pd.DataFrame
        The feature matrix produced by FeaturePipeline.fit_transform() or
        FeaturePipeline.transform().
    s3_uri : str
        Destination S3 URI, e.g.
        ``s3://my-bucket/tenants/abc123/features/train.parquet``.
        If the URI does not end with ``.parquet`` the function appends it.
    tenant_id : str
        Tenant identifier added as a column to the Parquet file for
        traceability.
    boto_session : boto3.Session, optional
        Custom boto3 session (useful for testing / cross-account access).
        Defaults to the default session.

    Returns
    -------
    str
        The resolved S3 URI where the file was written.
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"s3_uri must start with 's3://', got: {s3_uri!r}")

    if not s3_uri.endswith(".parquet"):
        s3_uri = s3_uri.rstrip("/") + ".parquet"

    # Parse bucket and key
    without_scheme = s3_uri[len("s3://"):]
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri!r}")

    # Attach tenant_id for traceability
    df_out = feature_matrix.copy()
    df_out.insert(0, "tenant_id", tenant_id)

    # Serialise to Parquet in-memory
    buf = io.BytesIO()
    df_out.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)

    session = boto_session or boto3.Session()
    s3_client = session.client("s3")
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=buf.getvalue(),
        ContentType="application/octet-stream",
    )

    logger.info(
        "Feature matrix (%d rows × %d cols) written to %s",
        len(df_out),
        len(df_out.columns),
        s3_uri,
    )
    return s3_uri
