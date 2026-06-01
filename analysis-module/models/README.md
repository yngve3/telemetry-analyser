# Model Artifacts

This directory is reserved for runtime model artifacts used by `analysis-module`.

## Isolation Forest

The Isolation Forest detector looks for a trained artifact in this location when
no explicit `isolation_forest_artifact_path` is provided:

- `analysis-module/models/isolation_forest`

The artifact must contain:

- `model.joblib`
- `scaler.joblib`
- `metadata.json`

`metadata.json` must describe the feature contract used during training:

- `model_type`
- `feature_names`
- `window_size`
- `threshold`
- `feature_statistics` with `mean`, `std`, `min`, and `max` per feature

The current artifact was produced by
`training/scripts/training/train_isolation_forest.py`. Runtime loading requires
`joblib` and `scikit-learn`.

## Autoencoder

The autoencoder detector looks for an artifact in one of these locations when no
explicit `model_artifact_path` is provided:

- `analysis-module/models/autoencoder_px4`
- `analysis-module/models/autoencoder`
- `analysis-module/models/autoencoder.zip`

The current PX4 autoencoder artifact must contain:

- `model.pt`
- `metadata.json`
- `scaler.joblib`

`metadata.json` stores `feature_names`, `window_size`, `input_dim`,
`latent_dim`, `threshold`, and optional `feature_statistics`. If the artifact is
missing or cannot be loaded, the detector reports `not_ready` instead of running
a statistical fallback. Runtime neural inference requires PyTorch; explicit
invalid artifact paths are treated as configuration errors.

## Adaptive Correlation Profile

The adaptive correlation detector can start from a saved JSON profile. When no
explicit `adaptive_correlation_profile_path` is provided, the analyzer factory
checks these files:

- `analysis-module/models/adaptive_correlation_profile.json`
- `analysis-module/models/adaptive_correlation_profile`

The file should use the same shape returned by
`AdaptiveCorrelationProfile.to_dict()`:

```json
{
  "max_size": 1000,
  "min_samples": 100,
  "percentile": 0.99,
  "threshold_multiplier": 1.2,
  "errors": {
    "position_speed_error": [],
    "altitude_velocity_error": [],
    "heading_yaw_error": []
  }
}
```

Only the profile data belongs in this file. Runtime persistence, if needed,
should be implemented in an infrastructure adapter rather than inside the
detector.
