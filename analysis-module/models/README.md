# Model Artifacts

This directory is reserved for runtime model artifacts used by `analysis-module`.

The autoencoder detector looks for an artifact in one of these locations when no
explicit `model_artifact_path` is provided:

- `analysis-module/models/autoencoder`
- `analysis-module/models/autoencoder.zip`

An autoencoder artifact must contain:

- `model.pt`
- `metadata.json`
- `normalizer.json`
- `threshold.json`

The current runtime validates this artifact contract and uses the artifact
threshold and metadata through the scoring interface. Real neural inference can
be added later by replacing the artifact-backed scoring model implementation
without changing the analyzer API.
