# Synthetic Mission Script

`MissionScript` is the human-friendly input format for synthetic missions. It is intended for UI forms and JSON import/export.

The generator should not execute `MissionScript` directly. Scripts are compiled into `MissionPlan`, which remains the normalized runtime model for mission playback.

## Flow

```text
MissionScript
-> MissionScriptValidator
-> MissionScriptCompiler
-> MissionPlan
-> MissionRunner
-> TelemetrySample
```

`MissionScriptValidator` checks the user-authored structure before compilation. `MissionScriptCompiler` converts relative steps such as `move_forward` and `turn` into executable mission phases with absolute target coordinates, target altitude, heading, speed, and duration.

Mission scripts can include optional profiles for motion, noise, and battery drain. These profiles keep generator behavior configurable without moving transport or API concerns into the domain model.

## Supported Steps

- `takeoff` - climb to a target altitude;
- `move_forward` - move by distance at speed using current heading;
- `turn` - change heading by angle;
- `hover` - hold position for a duration;
- `return_home` - move back to the home point;
- `landing` - descend to ground level.

## Runtime Commands

The synthetic mission runtime accepts commands through `MissionCommand`:

- `inject_anomaly` - schedules a synthetic anomaly relative to current mission time;
- `set_parameter` - applies a runtime override such as `target_speed`;
- `pause` - pauses mission time;
- `resume` - resumes mission time;
- `stop` - stops mission playback and resets elapsed time.

## API Usage

Create a mission through:

```text
POST /sources/synthetic/missions
```

Start playback:

```text
POST /sources/synthetic/missions/{mission_id}/start
```

Generate a batch of telemetry samples:

```text
GET /sources/synthetic/missions/{mission_id}/samples?count=10
```

Submit an anomaly command:

```json
{
  "command": "inject_anomaly",
  "type": "GPS_SPOOFING",
  "start_after_sec": 5,
  "duration_sec": 10,
  "intensity": 0.7
}
```

Submit a parameter override command:

```json
{
  "command": "set_parameter",
  "name": "target_speed",
  "value": 12
}
```

`target_speed` changes are reflected in movement calculations. Active movement phases are recalculated from the remaining distance, while future movement phases are recalculated from their full distance.

Start continuous MAVLink-over-UDP publication for a mission:

```text
POST /streams/synthetic/missions/{mission_id}/udp
```

```json
{
  "host": "analysis-service",
  "port": 14560,
  "frequency_hz": 20
}
```

## Example

```json
{
  "name": "simple_mission",
  "frequency_hz": 20,
  "home": {
    "latitude": 47.397742,
    "longitude": 8.545594,
    "altitude": 0,
    "heading_deg": 0,
    "battery": 100
  },
  "motion_profile": {
    "horizontal_acceleration_m_s2": 2.0,
    "default_climb_rate_m_s": 3.0,
    "default_descent_rate_m_s": 2.0,
    "default_yaw_rate_deg_s": 45.0,
    "default_return_speed_m_s": 8.0
  },
  "noise_profile": {
    "random_seed": 42,
    "gps_position_std_m": 0.4,
    "altitude_std_m": 0.2,
    "speed_std_m_s": 0.1,
    "heading_std_deg": 0.5,
    "battery_std_percent": 0.0
  },
  "battery_profile": {
    "takeoff_percent_per_sec": 0.025,
    "waypoint_percent_per_sec": 0.015,
    "turn_percent_per_sec": 0.01,
    "hover_percent_per_sec": 0.012,
    "return_home_percent_per_sec": 0.015,
    "landing_percent_per_sec": 0.01
  },
  "steps": [
    { "type": "takeoff", "target_altitude": 30 },
    { "type": "move_forward", "distance_m": 100, "speed_m_s": 8 },
    { "type": "turn", "direction": "right", "angle_deg": 90 },
    { "type": "move_forward", "distance_m": 80, "speed_m_s": 8 },
    { "type": "hover", "duration_sec": 10 },
    { "type": "return_home", "speed_m_s": 8 },
    { "type": "landing" }
  ]
}
```

## Boundary

This model belongs only to the synthetic source. Snapshot and external source modes should not depend on mission script classes.
