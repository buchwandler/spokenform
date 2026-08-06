"""Map a source range into the expanded spoken output."""

from spokenform import prepare

source = "Prof. Klein has 2 kg."
prepared = prepare(source, language="de")
assert prepared.offset_map is not None

start = source.index("Prof.")
end = start + len("Prof.")
spoken_start, spoken_end = prepared.offset_map.map_source_span(start, end)

print(prepared.spoken_text)
print(prepared.spoken_text[spoken_start:spoken_end])
