"""English number categories remain caller-managed pending parity gates."""

from ..config import NumberPolicy

NUMBER_POLICY = NumberPolicy.CALLER_MANAGED

__all__ = ["NUMBER_POLICY"]
