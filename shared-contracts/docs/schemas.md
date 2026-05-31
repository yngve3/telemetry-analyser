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
- system status, flight mode, arming state, and sensor health flags;
- per-channel freshness fields and `message_quality` for stream conversion.

## anomaly-result.schema.json

Describes anomaly analysis results produced by `analysis-module` and consumed by viewers, storage, or APIs.

Each final anomaly includes its type, severity, user-facing message, merged
confidence, and `sources`. Each source identifies the detector that contributed
evidence to the aggregate anomaly.

Final anomalies also include diagnostic fields for operational interpretation:
`probable_cause`, `cause_confidence`, `diagnostic_evidence`, and
`recommended_action`.

`detector_outputs` contains raw outputs from enabled detectors. Disabled
detectors are omitted.

Model-based detectors that do not map a score to a concrete anomaly category use
`ANOMALOUS_BEHAVIOR`.

## flight-scenario.schema.json

Describes a portable synthetic flight scenario: home point, command-like flight
steps, frequency, and scheduled anomaly injection. It is an exchange contract for
source configuration, not the internal generator domain model.

## telemetry-source-config.schema.json

Describes the source mode selected by the telemetry source application:
synthetic, snapshot, or external. It also defines the publication settings used
when samples are encoded and sent through a transport.
