#!/usr/bin/env python3
"""Inject an application-owned spaCy pipeline instead of loading by model name."""

from __future__ import annotations

import spacy

from spokenform import prepare

nlp = spacy.load("de_core_news_sm")
prepared = prepare(
    "Prof. Klein liefert 2 kg.",
    language="de",
    nlp=nlp,
)

print(prepared.spoken_text)
