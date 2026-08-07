"""German locale ownership metadata.

German structured grammar remains implemented in :mod:`spokenform.structured`
while the dispatcher is migrated incrementally; this module is the stable locale
boundary for policy and future grammar extraction.
"""

from ..config import NumberPolicy

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN

__all__ = ["NUMBER_POLICY"]
