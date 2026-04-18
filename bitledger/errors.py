"""Typed exceptions for BitLedger."""


class ProtocolError(Exception):
    """Protocol-level violation (invalid bit state, rule breach)."""


class EncoderError(Exception):
    """Encoding failed (overflow, invalid field combination)."""


class DecoderError(Exception):
    """Decoding or validation failed."""


class DecoderWarning(Exception):
    """Non-fatal decode observation: mismatch or anomaly that may affect interpretation.

    Attributes:
        message: Human-readable description of the issue.
        suggestion: Suggested remediation for the user.
        ref: Optional protocol element or doc reference.
        suppressed_by: Config key name that disables this warning.
    """

    def __init__(
        self,
        message: str,
        *,
        suggestion: str = "",
        ref: str = "",
        suppressed_by: str = "",
    ) -> None:
        super().__init__(message)
        self.suggestion = suggestion
        self.ref = ref
        self.suppressed_by = suppressed_by

    def format_compact(self) -> str:
        """Single-block warning output matching project error style."""
        lines = [f"WARN: {self}"]
        if self.suggestion:
            lines.append(f"  → {self.suggestion}")
        if self.ref:
            lines.append(f"  ref: {self.ref}")
        if self.suppressed_by:
            lines.append(f"  (suppress: set {self.suppressed_by}=false in master config)")
        return "\n".join(lines)


class ProfileError(Exception):
    """Profile / currency lookup error."""
