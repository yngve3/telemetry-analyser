# Synthetic Anomaly Injection

Synthetic anomalies are modeled as domain strategies.

## Structure

```text
backend/src/telemetry_source_backend/domain/synthetic/
  models/
      anomaly_profile.py
      anomaly_type.py
  services/
    anomaly_injection/
      anomaly_injector.py
      gps_signal_loss_injector.py
      gps_spoofing_injector.py
      imu_spike_injector.py
      motion_inconsistency_injector.py
      battery_drop_injector.py
      low_battery_injector.py
      telemetry_freeze_injector.py
      telemetry_gap_injector.py
      impossible_altitude_injector.py
      anomalous_behavior_injector.py
      registry.py
```

## Extension Flow

To add a new synthetic anomaly type:

1. Add a value to `AnomalyType`.
2. Add an injector implementing `AnomalyInjector`.
3. Register the injector in `default_anomaly_registry`.
4. Add domain tests for the new injection behavior.

`SyntheticTelemetryFactory` applies anomalies through the registry. It does not need to know the implementation details of each anomaly type.

This extension point belongs only to the synthetic source. Snapshot and external source modes should not depend on anomaly injectors.
