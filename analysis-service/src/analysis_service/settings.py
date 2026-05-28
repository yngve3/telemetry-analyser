"""Analysis service settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Analysis Service"
    app_version: str = "0.1.0"
