# analysis-module Architecture

`analysis-module` owns the anomaly analysis domain. It works only with internal telemetry models and returns analysis results.

## Layers

- `domain` - telemetry, anomaly, severity, and result models;
- `application` - analyzer contract, configuration, factories, and result aggregation;
- `features` - bounded telemetry history and stable feature extraction;
- `detectors` - deterministic rules and future model-based scoring adapter;
- `infrastructure` - filesystem model artifact loading.

## Runtime Flow

```text
UnifiedTelemetry
-> TelemetryHistory
-> AnalysisContext
-> enabled TelemetryDetector implementations
-> ResultAggregator
-> AnomalyResult
```

`TelemetryAnalyzer.analyze_next()` is intentionally stateful because several
anomalies depend on previous samples or a recent window.

For an external `analysis-service`, the service owns HTTP concerns, sessions,
profiles, and input conversion. Detector orchestration and aggregation stay in
`analysis-module`: the service creates an analyzer from a profile, passes
`UnifiedTelemetry`, and receives one `AnomalyResult` containing both aggregated
`anomalies` and raw `detector_outputs`.

## Detector Families

- `rule_based` - deterministic rules implemented in this module;
- `ml` - prepared scoring detector contract for classical ML artifacts;
- `nn` - prepared scoring detector contract for neural-network artifacts.

The ML and NN detectors are placeholders until real model loaders are added. They
share the same `TelemetryScoringModel` contract. Enabling `ml` or `nn` without an
artifact path is rejected by the factory. When a model score is above threshold
without a more specific domain anomaly type, the detector returns
`ANOMALOUS_BEHAVIOR`.

## Boundary

The module must not depend on MAVLink, telemetry source applications, viewers, APIs, storage, or transports. External systems should provide data as `UnifiedTelemetry`.

Model artifacts are infrastructure inputs. The domain layer knows only anomaly
models and rule contracts; loading files from disk belongs to infrastructure.
