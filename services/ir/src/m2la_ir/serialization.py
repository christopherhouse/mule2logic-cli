"""JSON serialization and deserialization for the IR."""

from m2la_ir.models import MuleIR


def to_json(ir: MuleIR) -> str:
    """Serialize a MuleIR to formatted JSON.

    Args:
        ir: The IR to serialize.

    Returns:
        A JSON string with 2-space indentation.
    """
    return ir.model_dump_json(indent=2)


def from_json(json_str: str) -> MuleIR:
    """Deserialize a MuleIR from JSON.

    Args:
        json_str: A JSON string representing a MuleIR.

    Returns:
        The deserialized MuleIR instance.
    """
    return MuleIR.model_validate_json(json_str)
