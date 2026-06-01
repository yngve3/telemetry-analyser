# analysis-module Architecture

`analysis-module` owns the anomaly analysis domain. It works only with internal telemetry models and returns analysis results.

## Layers

- `domain` - telemetry, anomaly, severity, and result models;
- `application` - analyzer contract, configuration, factories, and result aggregation;
- `features` - bounded telemetry history and stable feature extraction;
- `detectors` - deterministic rules and model-based detector implementations;
- `infrastructure` - filesystem model artifact loading.

## Runtime Flow

```text
UnifiedTelemetry
-> TelemetryHistory
-> AnalysisContext
-> enabled TelemetryDetector implementations
-> ResultAggregator
-> CauseDiagnosisLayer
-> AnomalyResult
```

`TelemetryAnalyzer.analyze_next()` is intentionally stateful because several
anomalies depend on previous samples or a recent window.

For an external `analysis-service`, the service owns HTTP concerns, sessions,
profiles, and input conversion. Detector orchestration and aggregation stay in
`analysis-module`: the service creates an analyzer from a profile, passes
`UnifiedTelemetry`, and receives one `AnomalyResult` containing both aggregated
`anomalies` and raw `detector_outputs`.

The module owns result aggregation and probable-cause enrichment. The service
does not merge detector findings. It only selects a profile, calls the analyzer,
and returns the module-produced result.

## Detector Families

- `rule_based` - deterministic rules implemented in this module;
- `model_based` - extensible family for concrete model detectors.

Implemented model-based detectors:

- `correlation_based` - analyzes temporal dynamics and relationships between
  telemetry channels;
- `adaptive_correlation_based` - analyzes the same consistency relationships
  with a session-local profile of normal errors;
- `isolation_forest` - loads a trained sklearn Isolation Forest artifact when
  available, otherwise uses the built-in recent-window baseline;
- `autoencoder` - reports reconstruction-error anomalies as a pluggable
  model-based detector.

The autoencoder detector can run without an artifact by using the built-in
reconstruction baseline. If `model_artifact_path` points to a valid artifact, or
an artifact is present under `analysis-module/models/autoencoder(.zip)`, the
detector uses the artifact-backed scoring interface. The artifact layout is
documented in `analysis-module/models/README.md`.

The Isolation Forest detector can load `analysis-module/models/isolation_forest`
or an explicit `AnalyzerConfig.isolation_forest_artifact_path`. Its artifact was
produced by the training scripts and contains `model.joblib`, `scaler.joblib`,
and `metadata.json`.

Graph-based models are a future extension point. They are documented here to keep
the architecture open for parameter-relationship analysis without adding a heavy
graph implementation to the current version.

Classical ML and neural-network models are not separate analyzer levels. They are
concrete detector implementations under `DetectorKind.MODEL_BASED`. If a
model-based detector cannot classify an anomaly as a concrete domain type, it
returns `ANOMALOUS_BEHAVIOR`.

## Adaptive Profile Updates

Adaptive detectors do not update their profiles inside `analyze()`. They expose a
pending profile update and wait for the pipeline-level decision:

```text
detectors produce outputs
-> ResultAggregator builds final AnomalyResult
-> if AnomalyResult has no anomalies: commit profile update
-> otherwise: discard profile update
```

This keeps the normal-behavior profile from learning confirmed anomalous
telemetry. The adaptive correlation detector still uses static thresholds before
its profile is ready, so analysis remains useful without an initial calibration
flight. A normal calibration segment improves the adaptive thresholds but is not
required for startup.

Profile persistence is represented as plain data through `to_dict()` and
`from_dict()`. Reading or writing a profile file belongs to an infrastructure
adapter outside the detector.

The application factory can initialize the adaptive profile from a JSON file.
An explicit `AnalyzerConfig.adaptive_correlation_profile_path` takes priority.
Without it, the factory checks `analysis-module/models/adaptive_correlation_profile.json`
and `analysis-module/models/adaptive_correlation_profile`.

## Boundary

The module must not depend on MAVLink, telemetry source applications, viewers, APIs, storage, or transports. External systems should provide data as `UnifiedTelemetry`.

Model artifacts are infrastructure inputs. The domain layer knows only anomaly
models and rule contracts; loading files from disk belongs to infrastructure.
