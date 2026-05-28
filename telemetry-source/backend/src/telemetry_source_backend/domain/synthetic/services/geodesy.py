"""Small geodesy helpers for synthetic missions."""

import math

EARTH_RADIUS_M = 6_371_000.0


def move(
    latitude: float,
    longitude: float,
    heading_deg: float,
    distance_m: float,
) -> tuple[float, float]:
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    bearing_rad = math.radians(heading_deg)
    angular_distance = distance_m / EARTH_RADIUS_M

    target_lat = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )
    target_lon = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(target_lat),
    )

    return math.degrees(target_lat), math.degrees(target_lon)


def distance(
    start_latitude: float,
    start_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    start_lat = math.radians(start_latitude)
    target_lat = math.radians(target_latitude)
    delta_lat = math.radians(target_latitude - start_latitude)
    delta_lon = math.radians(target_longitude - start_longitude)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(start_lat) * math.cos(target_lat) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing(
    start_latitude: float,
    start_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    start_lat = math.radians(start_latitude)
    target_lat = math.radians(target_latitude)
    delta_lon = math.radians(target_longitude - start_longitude)

    y = math.sin(delta_lon) * math.cos(target_lat)
    x = math.cos(start_lat) * math.sin(target_lat) - math.sin(start_lat) * math.cos(
        target_lat
    ) * math.cos(delta_lon)
    return normalize_heading(math.degrees(math.atan2(y, x)))


def normalize_heading(heading_deg: float) -> float:
    return heading_deg % 360

