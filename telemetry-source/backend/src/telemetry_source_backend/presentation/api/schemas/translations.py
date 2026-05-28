"""Translation API response schemas."""

from pydantic import BaseModel


class LanguageResponse(BaseModel):
    code: str
    label: str


class TranslationsResponse(BaseModel):
    default_language: str
    languages: list[LanguageResponse]
    messages: dict[str, dict[str, str]]
