"""German semantic grammar owned by spokenform.

Symbol recognition belongs to :mod:`abbr2words`. This module only records the
linguistic facts needed after a canonical quantity identity has been matched.
"""

from dataclasses import dataclass

from ..config import NumberPolicy


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    """German realization facts for one abbr2words canonical identity."""

    canonical_id: str
    gender: str
    singular: str
    plural: str
    invariant_plural: bool = False


NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN

QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "f", "Sekunde", "Sekunden"),
    "duration-minute": QuantityGrammar("duration-minute", "f", "Minute", "Minuten"),
    "duration-hour": QuantityGrammar("duration-hour", "f", "Stunde", "Stunden"),
    "duration-day": QuantityGrammar("duration-day", "m", "Tag", "Tage"),
    "length-millimeter": QuantityGrammar("length-millimeter", "m", "Millimeter", "Millimeter"),
    "length-centimeter": QuantityGrammar("length-centimeter", "m", "Zentimeter", "Zentimeter"),
    "length-meter": QuantityGrammar("length-meter", "m", "Meter", "Meter"),
    "length-kilometer": QuantityGrammar("length-kilometer", "m", "Kilometer", "Kilometer"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "m", "Milliliter", "Milliliter"),
    "volume-liter": QuantityGrammar("volume-liter", "m", "Liter", "Liter"),
    "mass-microgram": QuantityGrammar("mass-microgram", "m", "Mikrogramm", "Mikrogramm"),
    "mass-milligram": QuantityGrammar("mass-milligram", "n", "Milligramm", "Milligramm"),
    "mass-gram": QuantityGrammar("mass-gram", "n", "Gramm", "Gramm"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "n", "Kilogramm", "Kilogramm"),
    "mass-tonne": QuantityGrammar("mass-tonne", "f", "Tonne", "Tonnen"),
    "energy-kilowatt-hour": QuantityGrammar(
        "energy-kilowatt-hour", "f", "Kilowattstunde", "Kilowattstunden"
    ),
    "energy-watt-hour": QuantityGrammar("energy-watt-hour", "f", "Wattstunde", "Wattstunden"),
    "charge-milliampere-hour": QuantityGrammar(
        "charge-milliampere-hour", "f", "Milliamperestunde", "Milliamperestunden"
    ),
    "current-milliampere": QuantityGrammar(
        "current-milliampere", "n", "Milliampere", "Milliampere"
    ),
    "frequency-gigahertz": QuantityGrammar("frequency-gigahertz", "m", "Gigahertz", "Gigahertz"),
    "frequency-megahertz": QuantityGrammar("frequency-megahertz", "m", "Megahertz", "Megahertz"),
    "frequency-kilohertz": QuantityGrammar("frequency-kilohertz", "m", "Kilohertz", "Kilohertz"),
    "frequency-hertz": QuantityGrammar("frequency-hertz", "m", "Hertz", "Hertz"),
    "power-watt": QuantityGrammar("power-watt", "m", "Watt", "Watt"),
    "voltage-volt": QuantityGrammar("voltage-volt", "m", "Volt", "Volt"),
    "count-piece": QuantityGrammar("count-piece", "n", "Stück", "Stück", True),
    "magnitude-thousand": QuantityGrammar("magnitude-thousand", "m", "Tausend", "Tausend"),
    "magnitude-million": QuantityGrammar("magnitude-million", "f", "Million", "Millionen"),
    "magnitude-billion": QuantityGrammar("magnitude-billion", "f", "Milliarde", "Milliarden"),
}

__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar"]
