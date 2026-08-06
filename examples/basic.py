"""Smallest useful spokenform example."""

from spokenform import prepare

source = "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit."
prepared = prepare(source, language="de")

print(prepared.spoken_text)
