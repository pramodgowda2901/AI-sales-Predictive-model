"""
Unit tests for ml/features.py

Run with:
    python -m pytest ml/test_features.py -v
"""

import io
import pickle
from datetime import timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from features import (
    FEATURE_COLS,
    NUMERIC_COLS,
    FeaturePipeline,
    compute_deal_age,
    compute_historical_close_rate,
    compute_rolling_engagement,
    compute_stage_velocity,
    save_to_s3,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(**kwargs) -> pd.DataFrame:
    """Build a minimal deal DataFrame for testing."""
    base = {
        "created_at": ["2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z"],
        "stage": ["Prospecting", "Negotiation"],
        "won": [1, 0],
    }
    base.update(kwargs)
    return pd.DataFrame(base)


# ---------------------------------------------------------------------------
# compute_deal_age
# ---------------------------------------------------------------------------

class TestComputeDealAge:
    def test_returns_non_negative_floats(self):
        df = _make_df()
        result = compute_deal_age(df)
        assert (result >= 0).all()
        assert result.dtype == float

    def test_uses_close_date_when_present(self):
        df = _make_df(
            created_at=["2024-01-01T00:00:00Z"],
            close_date=["2024-01-31T00:00:00Z"],
            stage=["Prospecting"],
            won=[1],
        )
        result = compute_deal_age(df)
        assert result.iloc[0] == pytest.approx(30.0)

    def test_missing_created_at_returns_zero(self):
        df = _make_df(created_at=[None, "2024-01-01T00:00:00Z"])
        result = compute_deal_age(df)
        assert result.iloc[0] == 0.0


# ---------------------------------------------------------------------------
# compute_stage_velocity
# ---------------------------------------------------------------------------

class TestComputeStageVelocity:
    def test_no_column_returns_zeros(self):
        df = _make_df()
        result = compute_stage_velocity(df)
        assert (result == 0.0).all()

    def test_single_transition_returns_zero(self):
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Prospecting"],
            "won": [1],
            "stage_transitions": [[{"stage": "Prospecting", "entered_at": "2024-01-01T00:00:00Z"}]],
        })
        result = compute_stage_velocity(df)
        assert result.iloc[0] == 0.0

    def test_two_transitions_computes_mean_days(self):
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Negotiation"],
            "won": [1],
            "stage_transitions": [[
                {"stage": "Prospecting", "entered_at": "2024-01-01T00:00:00Z"},
                {"stage": "Negotiation", "entered_at": "2024-01-11T00:00:00Z"},
            ]],
        })
        result = compute_stage_velocity(df)
        assert result.iloc[0] == pytest.approx(10.0)

    def test_malformed_transition_returns_zero(self):
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Prospecting"],
            "won": [1],
            "stage_transitions": [["not-a-dict"]],
        })
        result = compute_stage_velocity(df)
        assert result.iloc[0] == 0.0


# ---------------------------------------------------------------------------
# compute_rolling_engagement
# ---------------------------------------------------------------------------

class TestComputeRollingEngagement:
    def test_no_column_returns_zeros(self):
        df = _make_df()
        result = compute_rolling_engagement(df)
        assert (result == 0.0).all()

    def test_counts_only_recent_signals(self):
        now = pd.Timestamp.utcnow()
        recent = (now - pd.Timedelta(days=5)).isoformat()
        old = (now - pd.Timedelta(days=20)).isoformat()
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Prospecting"],
            "won": [1],
            "signals": [[
                {"ingested_at": recent},
                {"ingested_at": recent},
                {"ingested_at": old},   # outside 14-day window
            ]],
        })
        result = compute_rolling_engagement(df, window_days=14)
        assert result.iloc[0] == 2.0

    def test_empty_signals_returns_zero(self):
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Prospecting"],
            "won": [1],
            "signals": [[]],
        })
        result = compute_rolling_engagement(df)
        assert result.iloc[0] == 0.0

    def test_custom_window(self):
        now = pd.Timestamp.utcnow()
        recent = (now - pd.Timedelta(days=3)).isoformat()
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"],
            "stage": ["Prospecting"],
            "won": [1],
            "signals": [[{"ingested_at": recent}]],
        })
        assert compute_rolling_engagement(df, window_days=2).iloc[0] == 0.0
        assert compute_rolling_engagement(df, window_days=7).iloc[0] == 1.0


# ---------------------------------------------------------------------------
# compute_historical_close_rate
# ---------------------------------------------------------------------------

class TestComputeHistoricalCloseRate:
    def test_maps_known_stages(self):
        df = _make_df(stage=["Prospecting", "Negotiation"])
        rates = {"Prospecting": 0.2, "Negotiation": 0.8}
        result = compute_historical_close_rate(df, rates)
        assert result.iloc[0] == pytest.approx(0.2)
        assert result.iloc[1] == pytest.approx(0.8)

    def test_unknown_stage_uses_global_mean(self):
        df = _make_df(stage=["Unknown"])
        rates = {"Prospecting": 0.2, "Negotiation": 0.8}
        result = compute_historical_close_rate(df, rates)
        assert result.iloc[0] == pytest.approx(0.5)

    def test_empty_rates_returns_half(self):
        df = _make_df(stage=["Prospecting"])
        result = compute_historical_close_rate(df, {})
        assert result.iloc[0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# FeaturePipeline
# ---------------------------------------------------------------------------

def _make_pipeline_df(n: int = 4) -> pd.DataFrame:
    """Create a small DataFrame suitable for FeaturePipeline tests."""
    now = pd.Timestamp.utcnow()
    recent = (now - pd.Timedelta(days=3)).isoformat()
    return pd.DataFrame({
        "created_at": ["2024-01-01T00:00:00Z"] * n,
        "stage": (["Prospecting", "Negotiation"] * (n // 2 + 1))[:n],
        "won": ([1, 0] * (n // 2 + 1))[:n],
        "signals": [[{"ingested_at": recent}, {"ingested_at": recent}]] * n,
        "stage_transitions": [[
            {"stage": "Prospecting", "entered_at": "2024-01-01T00:00:00Z"},
            {"stage": "Negotiation", "entered_at": "2024-01-11T00:00:00Z"},
        ]] * n,
    })


class TestFeaturePipeline:
    def test_fit_transform_returns_correct_columns(self):
        df = _make_pipeline_df()
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df)
        assert list(result.columns) == FEATURE_COLS

    def test_fit_transform_returns_correct_row_count(self):
        df = _make_pipeline_df(6)
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df)
        assert len(result) == 6

    def test_numeric_cols_are_scaled(self):
        """After StandardScaler the numeric columns should have ~zero mean."""
        df = _make_pipeline_df(10)
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df)
        for col in NUMERIC_COLS:
            assert abs(result[col].mean()) < 1e-9, f"{col} mean not ~0 after scaling"

    def test_stage_encoded_is_numeric(self):
        df = _make_pipeline_df()
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df)
        assert result["stage_encoded"].dtype in (float, np.float64)

    def test_transform_without_fit_raises(self):
        df = _make_pipeline_df()
        pipeline = FeaturePipeline()
        with pytest.raises(RuntimeError, match="fitted"):
            pipeline.transform(df)

    def test_transform_consistent_with_fit_transform(self):
        """transform() on the same data should produce the same result as fit_transform()."""
        df = _make_pipeline_df(8)
        pipeline = FeaturePipeline()
        X_fit = pipeline.fit_transform(df)
        X_transform = pipeline.transform(df)
        pd.testing.assert_frame_equal(X_fit, X_transform)

    def test_transform_unknown_stage_uses_minus_one(self):
        """Unknown stages at inference time should be encoded as -1."""
        df_train = _make_pipeline_df(4)
        pipeline = FeaturePipeline()
        pipeline.fit_transform(df_train)

        df_infer = df_train.copy()
        df_infer["stage"] = "BrandNewStage"
        result = pipeline.transform(df_infer)
        assert (result["stage_encoded"] == -1.0).all()

    def test_fit_transform_accepts_external_close_rates(self):
        df = _make_pipeline_df(4)
        close_rates = {"Prospecting": 0.3, "Negotiation": 0.7}
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df, close_rates=close_rates)
        assert result is not None
        assert "historical_close_rate" in result.columns

    def test_save_and_load_roundtrip(self, tmp_path):
        df = _make_pipeline_df(6)
        pipeline = FeaturePipeline()
        X_before = pipeline.fit_transform(df)

        path = str(tmp_path / "pipeline.pkl")
        pipeline.save(path)

        loaded = FeaturePipeline.load(path)
        X_after = loaded.transform(df)
        pd.testing.assert_frame_equal(X_before, X_after)

    def test_no_signals_column_returns_zero_engagement(self):
        df = pd.DataFrame({
            "created_at": ["2024-01-01T00:00:00Z"] * 4,
            "stage": ["Prospecting", "Negotiation"] * 2,
            "won": [1, 0] * 2,
        })
        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(df)
        assert (result["engagement_score"] == 0.0).all()


# ---------------------------------------------------------------------------
# save_to_s3
# ---------------------------------------------------------------------------

class TestSaveToS3:
    def _make_feature_matrix(self) -> pd.DataFrame:
        return pd.DataFrame({
            "deal_age": [1.0, 2.0],
            "stage_velocity": [0.5, 1.5],
            "engagement_score": [3.0, 0.0],
            "historical_close_rate": [0.4, 0.6],
            "stage_encoded": [0.0, 1.0],
        })

    def test_raises_on_invalid_uri(self):
        fm = self._make_feature_matrix()
        with pytest.raises(ValueError, match="s3://"):
            save_to_s3(fm, "not-an-s3-uri", "tenant-1")

    def test_raises_on_missing_key(self):
        fm = self._make_feature_matrix()
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            save_to_s3(fm, "s3://", "tenant-1")

    def test_appends_parquet_extension(self):
        fm = self._make_feature_matrix()
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.return_value = mock_s3

        uri = save_to_s3(fm, "s3://my-bucket/features/train", "t1", boto_session=mock_session)
        assert uri.endswith(".parquet")

    def test_puts_object_to_correct_bucket_and_key(self):
        fm = self._make_feature_matrix()
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.return_value = mock_s3

        save_to_s3(fm, "s3://my-bucket/tenants/t1/features/train.parquet", "t1", boto_session=mock_session)

        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "my-bucket"
        assert call_kwargs["Key"] == "tenants/t1/features/train.parquet"

    def test_output_parquet_contains_tenant_id_column(self):
        fm = self._make_feature_matrix()
        captured = {}

        def fake_put_object(**kwargs):
            captured["body"] = kwargs["Body"]

        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = fake_put_object
        mock_session.client.return_value = mock_s3

        save_to_s3(fm, "s3://bucket/key.parquet", "tenant-abc", boto_session=mock_session)

        result_df = pd.read_parquet(io.BytesIO(captured["body"]))
        assert "tenant_id" in result_df.columns
        assert (result_df["tenant_id"] == "tenant-abc").all()
