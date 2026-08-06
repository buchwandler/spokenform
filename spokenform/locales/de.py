"""Reviewed German unit metadata used by structured normalization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnitMetadata:
    aliases: tuple[str, ...]
    singular: str
    plural: str
    article: str
    category: str
    dotted_alias: bool = False


GERMAN_UNITS = (
    UnitMetadata(("kWh",), "Kilowattstunde", "Kilowattstunden", "eine", "energy"),
    UnitMetadata(("Wh",), "Wattstunde", "Wattstunden", "eine", "energy"),
    UnitMetadata(("GHz", "MHz", "kHz", "Hz"), "Hertz", "Hertz", "ein", "frequency"),
    UnitMetadata(("Std.",), "Stunde", "Stunden", "eine", "time", True),
    UnitMetadata(("Min.",), "Minute", "Minuten", "eine", "time", True),
    UnitMetadata(("Sek.",), "Sekunde", "Sekunden", "eine", "time", True),
    UnitMetadata(("Stck.",), "Stück", "Stücke", "ein", "count", True),
    UnitMetadata(("mAh",), "Milliamperestunde", "Milliamperestunden", "eine", "energy"),
    UnitMetadata(("mA",), "Milliampere", "Milliampere", "ein", "electric"),
    UnitMetadata(("kg", "g", "mg"), "Kilogramm", "Kilogramm", "ein", "mass"),
    UnitMetadata(("km", "cm", "mm", "m"), "Meter", "Meter", "ein", "length"),
    UnitMetadata(("m3", "m³"), "Kubikmeter", "Kubikmeter", "ein", "volume"),
    UnitMetadata(("ltr.",), "Liter", "Liter", "ein", "volume", True),
    UnitMetadata(("W", "V"), "Watt", "Watt", "ein", "electric"),
    UnitMetadata(("Tsd.",), "Tausend", "Tausend", "ein", "magnitude", True),
    UnitMetadata(("Mio.",), "Million", "Millionen", "eine", "magnitude", True),
    UnitMetadata(("Mrd.",), "Milliarde", "Milliarden", "eine", "magnitude", True),
)

__all__ = ["GERMAN_UNITS", "UnitMetadata"]
