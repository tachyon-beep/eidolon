from __future__ import annotations


class RulepackError(Exception):
    """Base class for rulepack-related failures."""


class RulepackSchemaError(RulepackError):
    """Raised when the rulepack document fails schema validation."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors

    def __str__(self) -> str:
        base = super().__str__()
        if not self.errors:
            return base
        return f"{base}: {'; '.join(self.errors)}"


class RulepackFormatError(RulepackError):
    """Raised when the rulepack document cannot be parsed."""
