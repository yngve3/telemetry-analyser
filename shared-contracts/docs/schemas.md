# Shared Schemas

`shared-contracts` defines stable exchange formats between independently developed modules.

## telemetry.schema.json

Describes a unified telemetry sample. Integration modules and source applications should use this structure when exchanging telemetry outside Python package boundaries.

`telemetry-source` validates generated telemetry against this schema before returning samples through the backend API or publishing MAVLink-over-UDP streams. The schema remains an exchange contract; Python domain objects are not imported across module boundaries.

The telemetry contract includes the fields required by the analysis pipeline:

- position, altitude, relative altitude, velocity, ground speed, and heading;
- attitude and angular rates;
- GPS fix type, satellite count, and GPS quality;
- battery remaining, voltage, and current;
- system status, flight mode, arming state, and sensor health flags.

## anomaly-result.schema.json

Describes anomaly analysis results produced by `analysis-module` and consumed by viewers, storage, or APIs.

Each final anomaly includes its type, severity, user-facing message, merged
confidence, and `sources`. Each source identifies the detector that contributed
evidence to the aggregate anomaly.

`detector_outputs` contains raw outputs from enabled detectors. Disabled
detectors are omitted.

Model-based detectors that do not map a score to a concrete anomaly category use
`ANOMALOUS_BEHAVIOR`.
