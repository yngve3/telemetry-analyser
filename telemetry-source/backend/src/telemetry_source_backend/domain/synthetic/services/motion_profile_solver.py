"""Motion profile calculations for synthetic missions."""

from math import sqrt


class MotionProfileSolver:
    """Solves simple trapezoidal/triangular movement profiles."""

    def duration_for_distance(
        self,
        distance_m: float,
        target_speed_m_s: float,
        acceleration_m_s2: float,
    ) -> float:
        if distance_m <= 0 or target_speed_m_s <= 0 or acceleration_m_s2 <= 0:
            return 0.1

        ramp_distance = target_speed_m_s**2 / acceleration_m_s2
        if distance_m >= ramp_distance:
            cruise_distance = distance_m - ramp_distance
            return (
                2 * target_speed_m_s / acceleration_m_s2
                + cruise_distance / target_speed_m_s
            )

        return 2 * sqrt(distance_m / acceleration_m_s2)

    def progress(
        self,
        elapsed_sec: float,
        duration_sec: float,
        distance_m: float,
        target_speed_m_s: float,
        acceleration_m_s2: float,
    ) -> float:
        if duration_sec <= 0 or distance_m <= 0:
            return 1.0

        elapsed_sec = min(max(elapsed_sec, 0.0), duration_sec)
        target_speed_m_s = max(target_speed_m_s, 0.0)
        acceleration_m_s2 = max(acceleration_m_s2, 0.0001)
        ramp_time = target_speed_m_s / acceleration_m_s2
        ramp_distance = target_speed_m_s**2 / acceleration_m_s2

        if distance_m >= ramp_distance:
            cruise_time = duration_sec - 2 * ramp_time
            if elapsed_sec <= ramp_time:
                covered = 0.5 * acceleration_m_s2 * elapsed_sec**2
            elif elapsed_sec <= ramp_time + cruise_time:
                covered = (
                    0.5 * acceleration_m_s2 * ramp_time**2
                    + target_speed_m_s * (elapsed_sec - ramp_time)
                )
            else:
                decel_time = elapsed_sec - ramp_time - cruise_time
                covered = (
                    0.5 * acceleration_m_s2 * ramp_time**2
                    + target_speed_m_s * cruise_time
                    + target_speed_m_s * decel_time
                    - 0.5 * acceleration_m_s2 * decel_time**2
                )
        else:
            peak_time = duration_sec / 2
            if elapsed_sec <= peak_time:
                covered = 0.5 * acceleration_m_s2 * elapsed_sec**2
            else:
                remaining_time = duration_sec - elapsed_sec
                covered = distance_m - 0.5 * acceleration_m_s2 * remaining_time**2

        return min(max(covered / distance_m, 0.0), 1.0)

