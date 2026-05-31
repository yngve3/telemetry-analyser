# analysis-module

Main Python module for UAV telemetry anomaly analysis.

The module accepts `UnifiedTelemetry` and returns `AnomalyResult`. It does not depend on MAVLink, telemetry source applications, viewers, APIs, WebSocket, or any other transport layer.

## Public API

The package is intended to be consumed as a Python library:

```python
from analysis_module import create_default_analyzer

analyzer = create_default_analyzer()
result = analyzer.analyze_next(telemetry)
```

Stable public imports are kept in `analysis_module.__init__`:

- `UnifiedTelemetry`
- `AnomalyResult`
- `AnalysisResult`
- `PipelineAnalysisResult`
- `AnomalySource`
- `DetectedAnomaly`
- `AnomalyType`
- `Severity`
- `AnalysisContext`
- `CauseDiagnosis`
- `CauseDiagnosisLayer`
- `DetectorKind`
- `DetectorOutput`
- `DetectorStatus`
- `TelemetryAnalyzer`
- `TelemetryDetector`
- `AnalyzerConfig`
- `create_default_analyzer()`
- `create_rule_based_analyzer()`
- `create_rule_based_detector()`
- `create_correlation_based_detector()`
- `create_isolation_forest_detector()`
- `create_autoencoder_detector()`
- `create_detectors()`
- `create_analyzer()`

## Package Layout

- `domain` - domain models for telemetry and analysis results;
- `application` - analyzer contract, configuration, factories, and result aggregation;
- `detectors` - rule-based and model-based detector adapters;
- `features` - telemetry history and stable feature extraction;
- `infrastructure` - external artifact loading adapters.

## Analyzer Contract

Analyzers implement a simple application-layer contract:

Simple library usage:

```text
UnifiedTelemetry -> analyzer-owned history/window -> detectors -> aggregation -> diagnosis -> AnomalyResult
```

Service orchestration usage:

```text
UnifiedTelemetry -> DetectorPipelineAnalyzer -> AnomalyResult
```

The domain model remains independent from transport formats and delivery mechanisms.

`analyze_next()` is stateful: the analyzer evaluates the current sample against
bounded history and appends the sample after detector evaluation.

For `analysis-service`, keep HTTP/API/session/profile management outside the
library. The service creates an analyzer from `AnalyzerConfig`, passes
`UnifiedTelemetry`, and receives one `AnomalyResult` with aggregated `anomalies`
and raw `detector_outputs`.

## Rule-Based Detection

The default analyzer registers separate deterministic rules:

- `GPS_SIGNAL_LOSS`
- `GPS_SPOOFING`
- `IMU_SPIKE`
- `BATTERY_DROP`
- `LOW_BATTERY`
- `IMPOSSIBLE_ALTITUDE`
- `TELEMETRY_FREEZE`
- `TELEMETRY_GAP`
- `MOTION_INCONSISTENCY`

Each detected anomaly contains `confidence`, `detector_name`, and detector-specific
`evidence`.

Final pipeline anomalies are grouped by `AnomalyType`. Their `sources` show which
detectors contributed evidence to the aggregate anomaly. The diagnostic layer
adds `probable_cause`, `cause_confidence`, `diagnostic_evidence`, and
`recommended_action`.

## Detector Families

The library exposes deterministic rules and an extensible model-based detector
family for service-level enable/disable logic:

- `rule_based` - fully implemented deterministic rules;
- `correlation_based` - cross-channel checks over temporal dynamics and
  relationships between telemetry parameters;
- `isolation_forest` - trainable baseline fitted on a recent normal-behavior
  feature window;
- `autoencoder` - reconstruction-error detector exposed as one pluggable
  model-based detector.

All non-rule detectors use `DetectorKind.MODEL_BASED`. The library does not
position classical ML and neural networks as separate analysis levels; they are
concrete implementations under the same model-based extension point. When a
model-based detector finds an anomaly without a concrete domain type, it returns
`ANOMALOUS_BEHAVIOR`.

`GraphBasedDetector` is a documented extension point for future relationship
models, not part of the current implementation.

Unknown detector names are rejected by `create_detectors()` with
`DetectorConfigurationError`.

## Feature Extraction

`TelemetryFeatureExtractor` emits features in a fixed order. This order is part of
the model contract and must not change without a feature version bump.

## Model Artifact Contract

The model-based layer validates artifact packages but does not require PyTorch or
sklearn at runtime. A future artifact package must use either a directory or a
zip file with this structure:

```text
autoencoder_artifact/
  model.pt
  metadata.json
  normalizer.json
  threshold.json
```

`metadata.json`:

```json
{
  "model_type": "autoencoder",
  "feature_version": "1.0",
  "window_size": 50,
  "feature_names": [
    "battery_percent",
    "battery_voltage_v",
    "satellites_visible",
    "gps_fix_type",
    "gps_eph",
    "gps_epv",
    "altitude_m",
    "ground_speed_m_s",
    "vertical_speed_m_s",
    "roll_rad",
    "pitch_rad",
    "yaw_rad",
    "roll_rate_rad_s",
    "pitch_rate_rad_s",
    "yaw_rate_rad_s",
    "delta_position_m",
    "delta_altitude_m",
    "delta_battery_percent",
    "delta_heading_deg",
    "elapsed_sec",
    "attitude_age_ms",
    "position_age_ms",
    "gps_age_ms",
    "system_age_ms",
    "message_quality"
  ],
  "created_at": "2026-05-24T00:00:00Z"
}
```

`feature_names` must exactly match the stable order emitted by
`TelemetryFeatureExtractor`.

When no `model_artifact_path` is provided, the autoencoder detector also checks
for `analysis-module/models/autoencoder` and
`analysis-module/models/autoencoder.zip`. The current artifact-backed runtime is
a placeholder scoring adapter: it validates the artifact and uses its threshold
and metadata through the neural model interface. Real model inference can be
added behind that interface without changing the analyzer API.

## Documentation

- [Architecture](docs/architecture.md)

## Running Tests

From the repository root:

```powershell
python -m unittest discover -s analysis-module\tests
```
