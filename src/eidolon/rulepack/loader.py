from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, ValidationError

from .errors import RulepackFormatError, RulepackSchemaError
from .models import Rulepack
from .schema import load_schema


class RulepackLoader:
    """Loads and validates rulepack documents."""

    def __init__(self, *, schema: dict[str, Any] | None = None) -> None:
        self.schema = schema or load_schema()
        self.validator = Draft202012Validator(self.schema)

    def load(self, path: Path) -> Rulepack:
        document = self._load_raw(path)
        self._validate(document, path)
        return Rulepack.from_dict(document)

    def parse(self, document: dict[str, Any]) -> Rulepack:
        if not isinstance(document, dict):
            raise RulepackFormatError("Rulepack payload must be a mapping")
        self._validate(document)
        return Rulepack.from_dict(document)

    def validate(self, path: Path) -> list[str]:
        document = self._load_raw(path)
        return self._collect_errors(document)

    def _load_raw(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise RulepackFormatError(f"Failed to parse YAML for {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise RulepackFormatError(f"Rulepack at {path} must be a mapping at the top level")
        return data

    def _validate(self, document: dict[str, Any], path: Path | None = None) -> None:
        errors = self._collect_errors(document)
        if errors:
            location = f" ({path})" if path else ""
            raise RulepackSchemaError(f"Rulepack schema validation failed{location}", errors)

    def _collect_errors(self, document: dict[str, Any]) -> list[str]:
        return [
            self._format_error(error)
            for error in sorted(self.validator.iter_errors(document), key=lambda err: tuple(err.path))
        ]

    @staticmethod
    def _format_error(error: ValidationError) -> str:
        path = ".".join(str(p) for p in error.path)
        prefix = f"{path}: " if path else ""
        return f"{prefix}{error.message}"
