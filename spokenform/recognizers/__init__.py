"""Semantic recognizers built on Spokenform sequence renderers."""

from .biology import iter_replacements as iter_biomedical_replacements
from .ranges import iter_replacements as iter_range_replacements
from .references import iter_replacements as iter_reference_replacements
from .sequences import iter_sequence_replacements

__all__ = [
    "iter_biomedical_replacements",
    "iter_range_replacements",
    "iter_reference_replacements",
    "iter_sequence_replacements",
]
