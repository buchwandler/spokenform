"""High-confidence atomic recognizers for structured character sequences."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal
from urllib.parse import urlsplit

from ..config import InterpretationMode
from ..dates import render_english_year, render_year
from ..diagnostics import TraceCollector
from ..evidence import EvidenceSession
from ..language import base_language, normalize_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme
from ..sequences import (
    SEGMENT_BOUNDARY,
    SequenceRenderPolicy,
    render_letters,
    render_sequence,
    vocabulary,
)
from .biology import iter_replacements as iter_biomedical_replacements
from .product import product_label_category, product_label_text
from .ranges import iter_replacements as iter_range_replacements
from .references import iter_replacements as iter_reference_replacements
from .temporal import countdown_is_plausible, countdown_text

_FRACTION_CHARS = "½⅓⅔¼¾⅛⅜⅝⅞⅕⅖⅗⅘⅙⅚"
_FRACTION_RE = re.compile(rf"(?<!\w)(?P<whole>\d+)?(?P<fraction>[{_FRACTION_CHARS}])(?!\w)")
_SLASH_FRACTION_RE = re.compile(
    r"(?<![\w/])(?P<whole>\d+)\s+(?P<numerator>\d+)\s*/\s*(?P<denominator>\d+)(?![\w/])|"
    r"(?<![\w/])(?P<numerator_only>\d+)\s*/\s*(?P<denominator_only>\d+)(?![\w/])"
)
_COORDINATE_RE = re.compile(
    r"(?<!\w)(?P<value>[+-]?\d+(?:[.,]\d+)?)\s*°(?:\s*(?P<direction>[NSEWO])\b)?(?!\s*[CF]\b)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(?<!\w)(?P<value>[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*%(?!\w)")
_HEIGHT_RE = re.compile(r"(?<!\w)(?P<meters>\d+)[,.](?P<centimeters>\d{2})\s*m\b", re.IGNORECASE)
_ES_POSTAL_RE = re.compile(
    r"(?<!\w)(?P<label>c[oó]digo\s+postal|postal|C\.P\.)\s*[:#]?\s*(?P<value>0\d{4})(?!\w)",
    re.IGNORECASE,
)
_COMPOUND_UNIT_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?\d+(?:[.,]\d+)?)?\s*(?P<unit>g/cm(?:³|3)|mol/l|l\s*/\s*100\s*km)(?!\w)",
    re.IGNORECASE,
)
_CURRENCY_SYMBOL_RE = re.compile(
    r"(?<!\w)(?:(?P<prefix>[€$£])\s*)?(?P<number>[+\-−]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?)(?![.,]\d)\s*(?P<suffix>[€$£])?(?!\w)"
)
_CURRENCY_MAGNITUDE_RE = re.compile(
    r"(?<!\w)(?P<symbol>[€$£])\s*(?P<number>[+\-−]?\d+(?:[.,]\d+)?)\s+(?P<magnitude>thousand|million|billion|tausend|million(?:en)?|milliard(?:en)?|mil|millón(?:es)?|milli(?:one|ardi)?)(?!\w)",
    re.IGNORECASE,
)
_EXCHANGE_EQUAL_RE = re.compile(
    r"(?<!\w)(?P<left_number>[+\-−]?(?:\d+(?:[.,]\d+)?))\s*"
    r"(?P<left_currency>[A-Z]{3}|[€$£])\s*=\s*"
    r"(?P<right_currency>[A-Z]{3}|[€$£])?\s*(?P<right_number>[+\-−]?(?:\d+(?:[.,]\d+)?))(?!\w)",
    re.IGNORECASE,
)
_EXCHANGE_TO_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?(?:\d+(?:[.,]\d+)?))\s*"
    r"(?P<currency>[A-Z]{3}|[€$£])\s+(?:to|für|a|vers|per)\s+"
    r"(?P<target>[A-Z]{3}|[€$£])(?!\w)",
    re.IGNORECASE,
)
_EXCHANGE_SLASH_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?(?:\d+(?:[.,]\d+)?))\s*"
    r"(?P<currency>[A-Z]{3})\s*/\s*(?P<target>[A-Z]{3})(?!\w)",
    re.IGNORECASE,
)
_ISBN_RE = re.compile(
    r"(?<!\w)(?P<label>ISBN(?:-1[03])?)(?:\s+|:)(?P<value>(?:97[89][ -]?)?\d(?:[\d -]*\d|X|x))(?!\w)",
    re.IGNORECASE,
)
_ISBN_LABEL_RE = re.compile(r"(?<!\w)(?P<label>ISBN(?:-1[03])?)(?!\w)", re.IGNORECASE)
_SPACED_ISBN_LABEL_RE = re.compile(
    r"(?<!\w)(?P<label>I\s+S\s+B\s+N(?:\s*[-–]?\s*1[03])?)(?!\w)", re.IGNORECASE
)
_ISBN_VALUE_RE = re.compile(r"(?<!\w)(?P<value>(?:97[89][ -]?)?\d(?:[\d -]*\d|X|x))(?!\w)")
_CODE_RE = re.compile(
    r"(?<!\w)(?P<value>(?=[A-Z0-9-]*[A-Z])[A-Z0-9]{1,8}-\d{1,8}(?:[A-Z]{1,4}\d{1,4})?(?:-[A-Z0-9]{1,8})*)(?!\w)"
)
_DOTTED_LEXICAL_RE = re.compile(r"(?<!\w)(?P<value>U\.N\.C\.L\.E\.)(?!\w)", re.IGNORECASE)
_ITALIAN_SERIAL_RE = re.compile(
    r"\bnumero\s+di\s+serie\s*(?:è|:)?\s*(?P<value>\d+(?:-\d+)+)(?!\w)", re.IGNORECASE
)
_PLATE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,3}\d{1,4}[A-Z]{1,3})(?!\w)")
_COMPACT_PLATE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{1,3}-[A-Z]{1,3}\d{1,4})(?!\w)")
_SPACED_PLATE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{1,3}-[A-Z]{1,3}\s+\d{1,4})(?!\w)")
_COMPACT_VEHICLE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{1,3}\d{3,5})(?!\w)")
_REVIEWED_VEHICLE_PREFIXES = frozenset({"BMW", "VW", "AUDI", "FORD", "TESLA"})
_PLATE_CONTEXT_RE = re.compile(
    r"(?<!\w)(?:license\s+plate|kennzeichen|plaque\s+d['’]immatriculation|matrícula)\s*[:#-]?\s*"
    r"(?P<value>[A-Z]{1,3}-[A-Z]{1,3}\s*\d{1,4})(?!\w)",
    re.IGNORECASE,
)
_VIN_RE = re.compile(r"(?<!\w)(?P<value>[A-HJ-NPR-Z0-9]{17})(?!\w)", re.IGNORECASE)
_VEHICLE_MODEL_RE = re.compile(
    r"(?P<brand>BMW|Mercedes|Audi|Volkswagen|VW|Ford|Tesla|Canon)\s+(?P<value>[A-Z]\d{1,4}[A-Z]?)(?!\w)",
    re.IGNORECASE,
)
_UUID_RE = re.compile(
    r"(?<![\w-])(?P<value>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?![\w-])"
)
_IPV4_RE = re.compile(r"(?<![\w.])(?P<value>\d{1,3}(?:\.\d{1,3}){3})(?![\w.])")
_MAC_RE = re.compile(r"(?<![\w:])(?P<value>(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})(?![\w:])")
_IBAN_RE = re.compile(
    r"(?<!\w)(?P<value>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,32})(?!\w)", re.IGNORECASE
)
_PHONE_RE = re.compile(
    r"(?<![\w,.])(?P<value>\+?(?:\([0-9]{2,4}\)|[0-9])[0-9 ()/.\-]{5,}[0-9])(?!\w)"
)
_PHONE_BLOCKING_CONTEXT_RE = re.compile(
    r"(?:isbn(?:-1[03])?|legal|section|article|version|release|serial(?:\s+number)?|numero\s+di\s+serie|sku|model|product(?:\s+code)?|imei|iccid|mac|ip|vin|pin|uuid|\u00a7|art\.)\s*[:#-]?\s*(?:is\s+|for\s+[^\n]{0,32}\s+is\s+|è\s+|e\s+)?$",
    re.IGNORECASE,
)
_EMERGENCY_RE = re.compile(
    r"\b(?:call|dial|emergency|notruf|emergencia|número\s+de\s+emergencia|urgence|numéro\s+d['’]urgence|emergenza|numero\s+di\s+emergenza)\s*[:#-]?\s*(?P<value>110|112|911|999)\b",
    re.IGNORECASE,
)
_VERSION_CONTEXT_RE = re.compile(
    r"(?P<label>\b(?:software[- ]version|version|release|ver\.?|build)\s*"
    r"(?:is|ist|est|es)?\s*[=:]?\s*)"
    r"(?P<value>v?\d+(?:\.\d+){2,}(?:[a-z]+\d*)?)",
    re.IGNORECASE,
)
_SOFTWARE_VERSION_RE = re.compile(
    r"(?P<label>\b(?:Python|iOS|macOS|Ubuntu|GTK\+|Qt|Node(?:\.js)?|Android|Fedora|Debian|Firefox|WordPress)\s+)"
    r"(?P<value>\d+(?:\.\d+){1,}(?:[A-Za-z]+\d*)?)",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"(?<!\w)(?P<value>v\d+(?:\.\d+){1,}(?:-[A-Za-z0-9]+)?)(?!\w)",
    re.IGNORECASE,
)
_GENERIC_DOTTED_VERSION_RE = re.compile(r"(?<![\w.])(?P<value>\d+(?:\.\d+){2,})(?![\w.])")
_URL_RE = re.compile(r"(?<!\w)(?:https?://|www\.)[^\s<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"(?<![\w./])(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|ai|dev|ly|co|uk|de|fr|es|it|pt|ca|us|jp|cn|info|biz|app|tech)"
    r"(?:/[^\s<>]*)?",
    re.IGNORECASE,
)
_ROMAN_PREFIX_CARDINAL_RE = re.compile(
    r"(?P<context>\b(?i:article|act|scene|chapter|volume|part|section|block|page|super\s+bowl|"
    r"artikel|seite|akt|szene|kapitel|band|teil|abschnitt|block|"
    r"acto|escena|capítulo|capitulo|parte|sección|seccion|bloque|"
    r"partie|acte|scène|scene|chapitre|section|bloc|"
    r"atto|scena|capitolo|volume|parte|sezione|blocco|"
    r"ato|cena|capítulo|capitulo|parte|seção|secao|bloco)\s+)"
    r"(?P<value>[IVXLCDM]{1,12})(?![A-Za-z])"
)
_ROMAN_PREFIX_ORDINAL_RE = re.compile(
    r"(?P<context>\b(?i:siglo|século|seculo)\s+)(?P<value>[IVXLCDM]{1,12})(?![A-Za-z])"
)
_ROMAN_SUFFIX_ORDINAL_RE = re.compile(
    r"(?P<value>[IVXLCDM]{1,12})(?P<suffix>[eE])?\s+"
    r"(?P<context>(?i:century|dynasty|jahrhundert|dynastie|siglo|siècle|siecle|secolo|dinastia|século|seculo))\b"
)
_ROMAN_YEAR_CONTEXT_RE = re.compile(
    r"(?P<context>\b(?i:year|from\s+the\s+year|dated|scheduled\s+for|constructed\s+in|built\s+in|"
    r"signed\s+in|won\s+in|held\s+in|im\s+jahr|aus\s+dem\s+jahr|anno|año|année|ano|"
    r"olympic\s+games|olympische\s+spiele|games|edition|event)\s+)"
    r"(?P<value>[IVXLCDM]{2,12})(?![A-Za-z])"
)
_ROMAN_CLOCK_RE = re.compile(
    r"(?P<context>\b(?i:clock\s+showed|clock\s+shows|uhr\s+zeigte|reloj\s+mostraba|"
    r"l['’]horloge\s+affichait|l['’]orologio\s+segnava|o\s+relógio\s+mostrava)\s+)"
    r"(?P<value>[IVXLCDM]{1,12})(?![A-Za-z])"
)
_ROMAN_NUMBERED_PREFIX_RE = re.compile(
    r"(?P<context>\b(?i:numbered|numerado|numéroté|numerote|numerato)\s+)"
    r"(?P<value>[IVXLCDM]{1,12})(?![A-Za-z])"
)
_ROMAN_NUMBERED_SUFFIX_RE = re.compile(
    r"(?P<context>\b(?i:mit)\s+)(?P<value>[IVXLCDM]{1,12})(?=\s+(?i:nummeriert)\b)"
)
_EN_MONARCH_RE = re.compile(
    r"(?P<context>\b(?:(?i:King|Queen|Pope)\s+)?(?i:Elizabeth|Charles|Henry|George)\s+)"
    r"(?P<value>[IVX]{1,12})\.?(?![A-Za-z])"
)
_DE_MONARCH_RE = re.compile(
    r"(?P<context>\b(?:(?i:Kaiser|König|Königin|Papst)\s+)?(?i:Heinrich|Wilhelm|Ludwig|Karl|Friedrich|Benedikt|Elisabeth)\s+)"
    r"(?P<value>[IVX]{1,12})\.?(?![A-Za-z])"
)
_FR_MONARCH_RE = re.compile(
    r"(?P<context>\b(?:(?i:roi)\s+)?(?i:Henri)\s+)(?P<value>[IVX]{1,12})\.?(?![A-Za-z])"
)
_IT_MONARCH_RE = re.compile(
    r"(?P<context>\b(?:(?i:Re)\s+)?(?i:Enrico)\s+)(?P<value>[IVX]{1,12})\.?(?![A-Za-z])"
)
_PT_MONARCH_RE = re.compile(
    r"(?P<context>\b(?:(?i:Rei)\s+)?(?i:Henrique)\s+)(?P<value>[IVX]{1,12})\.?(?![A-Za-z])"
)
_PAREN_INITIALISM_RE = re.compile(r"(?<!\w)\((?P<value>[A-Z]{2,8})\)(?!\w)")
_PAREN_TICKER_RE = re.compile(r"(?<!\w)\((?P<value>[A-Z])\)(?!\w)")
_HASHTAG_RE = re.compile(r"(?<!\w)#(?P<value>[\wÀ-ž](?:[\wÀ-ž_-]*[\wÀ-ž])?)", re.UNICODE)
_MENTION_RE = re.compile(r"(?<!\w)@(?P<value>[\wÀ-ž](?:[\wÀ-ž_-]*[\wÀ-ž])?)", re.UNICODE)
_FORMULA_RE = re.compile(
    r"(?<!\w)(?P<value>(?:(?:[A-Z][a-z]?)+|\((?:[A-Z][a-z]?)+\)[0-9₀-₉]+|[A-Z][a-z]?[0-9₀-₉]+)+)(?!\w)"
)
_MATH_ATOM = r"(?:√\s*)?(?:[A-Za-zπΔα-ωΑ-Ω]+|\d+(?:[.,]\d+)?|[|()]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?"
_MATH_RE = re.compile(
    rf"(?<![\w/+-])(?P<value>{_MATH_ATOM}(?:\s*(?:[+−*=×÷<>^\-/≈≠≤≥])\s*{_MATH_ATOM})+)(?![\w/+-])"
)
_MATH_ABSOLUTE_RE = re.compile(
    rf"(?<![\w/+-])(?P<value>\|[^|]+\|\s*(?:[=≈≠≤≥])\s*{_MATH_ATOM})(?![\w/+-])"
)
_SUPERSCRIPT_RE = re.compile(r"(?<!\w)(?P<base>[A-Za-z]+|\d+)(?P<exponent>²)(?!\w)")
_GREEK_TOKEN_RE = re.compile(r"(?<!\w)(?P<value>[αβγδεθλμπσφωΔΣΩ])(?!\w)")
_MUSIC_CONTEXT_RE = re.compile(
    r"\b(?:chord|note|key|tonality|akkord|stück|stück|tonart|nota|accord|accordo)\b[^\n,]{0,24}?"
    r"(?P<value>[A-Ga-g](?:[#b♯♭])?(?:[-]?(?:Dur|Moll)|m|maj|min|dim|sus)?\d*)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_TEMPO_RE = re.compile(r"(?P<note>[♩♪♫])\s*=\s*(?P<value>\d{1,3})(?!\w)")
_BIOLOGY_RE = re.compile(
    r"(?<!\w)(?P<value>[A-Z]\.\s*[a-z][a-z-]{2,}(?:\s+(?:strain|subsp\.)\s*[A-Za-z0-9-]+)?)(?!\w)"
)
_BIOLOGY_NON_SPECIES_WORDS = frozenset(
    {
        "headquarters",
        "general",
        "section",
        "operations",
        "enforcement",
        "department",
        "after",
        "before",
        "during",
    }
)
_MIXED_ACRONYM_RE = re.compile(r"(?<!\w)(?P<value>[A-Z][a-z]{1,4}[A-Z])(?!\w)")
_TICKER_RE = re.compile(r"(?<!\w)\$(?P<value>[A-Z]{1,5})(?!\w)")
_TICKER_CONTEXT_RE = re.compile(
    r"\b(?:ticker|stock\s+symbol|stock|symbol|acción|symbole|azione)\s*"
    r"(?:is|was|es|ist|est|è|:)?\s*(?P<value>[A-Z]{2,5})(?!\w)",
    re.IGNORECASE,
)
_EXCHANGE_TICKER_RE = re.compile(
    r"\b(?:NASDAQ|NYSE)\s*:\s*(?P<value>[A-Z]{2,5})(?!\w)",
    re.IGNORECASE,
)
_QUARTER_RE = re.compile(
    r"(?<![\w-])(?:(?P<fy>FY)\s*(?P<fy_year>\d{4})\s+)?"
    r"(?P<label>Q)(?P<quarter>[1-4])(?:\s+(?P<year>\d{4}))?(?![\w-])",
    re.IGNORECASE,
)
_PRODUCT_RE = re.compile(
    r"(?<!\w)(?P<label>License\s+plate|Tax\s+identifier|Serial\s+number|Part\s+number|Product\s+code|Bar(?:code|\s+code)|Matrikelnummer|Seriennummer|Kennzeichen|Registration|Identifier|ID|Tag|Plate|License|Firmware|RFC|P/N|SN|S/N|Serial|SKU|Model|Modelo|VIN|IMEI|ICCID|PIN|Part|Product|routing\s+number|account(?:\s+number)?)\s*(?:[:#-]\s*|\s+)(?:No\.\s*)?(?P<value>[A-Za-z0-9][A-Za-z0-9.-]{1,})",
    re.IGNORECASE,
)


def _valid_product_candidate(label: str, value: str) -> bool:
    """Require code evidence even when a strong label is followed by prose."""
    value = value.rstrip(".")
    if not value:
        return False
    label_key = label.casefold().replace(".", "").strip()
    if label_key in {"part", "part number"} and value.isalpha() and _roman_is_valid(value):
        return False
    if any(character.isdigit() for character in value):
        return True
    if re.search(r"(?<=\w)[./-](?=\w)", value):
        return True
    if value.isupper() and value.isalnum() and len(value) >= 2:
        return True
    return False


_LEGAL_RE = re.compile(
    r"(?<!\w)(?P<value>(?:§|Art\.?|Artikel)\s*\d+(?:\s+(?:Abs\.?\s*\d+|[IVXLCDM]+))?(?:\s+\d+)?\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{1,})(?!\w)",
)
_LEGAL_PREFIX_RE = re.compile(
    r"(?<!\w)(?P<value>(?:BGB|StGB|StVO|GG|VwGO|HGB|AO)\s+§\s*\d+(?:\s+Abs\.?\s*\d+)?)(?!\w)"
)
_LEGAL_US_RE = re.compile(r"(?<!\w)(?P<value>\d+\s+U\.S\.C\.\s+§\s*\d+)(?!\w)", re.IGNORECASE)
_LEGAL_ES_RE = re.compile(r"(?<!\w)(?P<value>ley\s+\d{1,3}(?:\.\d{3})?)(?!\w)", re.IGNORECASE)
_LEGAL_IT_RE = re.compile(r"(?<!\w)(?P<value>legge\s+n\.?\s*\d+(?:/\d{4})?)(?!\w)", re.IGNORECASE)
_LEGAL_ES_SLASH_RE = re.compile(
    r"(?<!\w)(?P<value>(?:sentencia|registro)\s+\d+/\d{4})(?!\w)", re.IGNORECASE
)
_LEGAL_IT_SLASH_RE = re.compile(
    r"(?<!\w)(?P<value>(?:legge|sentenza|regolamento)\s+(?:n\.?\s*)?\d+/\d{3,4})(?!\w)",
    re.IGNORECASE,
)
_LEGAL_DOCKET_RE = re.compile(
    r"(?<!\w)(?P<value>Docket\s+No\.?\s*\d{4}-\d+|Case\s+No\.?\s*\d+:\d+-[A-Za-z]+-\d+)(?!\w)",
    re.IGNORECASE,
)
_LEGAL_FR_RE = re.compile(
    r"(?<!\w)(?P<value>(?:décret|decret)\s+n[°o]?\s*\d{4}-\d+)(?!\w)", re.IGNORECASE
)
_LEGAL_LABEL_RE = re.compile(
    r"(?<!\w)(?P<value>(?:section|sec\.?|article|art\.?|chapter|chap\.)\s*\d+(?:\s+(?:subsection|paragraph|para\.?|§)\s*\d+)?)(?!\w)",
    re.IGNORECASE,
)
_SPORTS_RE = re.compile(
    r"(?P<context>\b(?:score|final|match|game|team|won|wins|football|basketball|handball|volleyball|"
    r"set|satz|ergebnis|endergebnis|gewann|gewannen|spiel|tabelle|statistik|torverhältnis|"
    r"basketballer|cricket|baseball|hockey|tennis|rugby|marcador|punteggio|partido|termin[oó]|"
    r"victoria|ganaron|empate|draw|résultat|resultado|ganó|gagné|vinto)\b[^\d]{0,32})"
    r"(?P<value>\d{1,3}\s*(?::|[-–])\s*\d{1,3}|\d{1,3}\s+(?:a|to|à)\s+\d{1,3})",
    re.IGNORECASE,
)
_SPORTS_CONTEXT_RE = re.compile(
    r"\b(?:score|final|match|game|team|won|wins|football|basketball|handball|volleyball|set|"
    r"result|resultat|resultado|satz|ergebnis|endergebnis|gewann|gewannen|spiel|tabelle|"
    r"statistik|torverhältnis|basketballer|cricket|baseball|hockey|tennis|rugby|marcador|"
    r"punteggio|partido|termin[oó]|victoria|ganaron|empate|draw|résultat|ganó|gagné|vinto)\b",
    re.IGNORECASE,
)
_SCORE_RE = re.compile(r"(?<!\w)(?P<value>\d{1,2}\s*(?::|[-–])\s*\d{1,2})(?![\w:-])")
_CHAINED_SCORE_RE = re.compile(r"(?<!\w)(?P<value>\d{1,2}(?:\s*[-–]\s*\d{1,2}){2,})(?![\w:-])")
_DURATION_RE = re.compile(r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>[0-5]\d):(?P<second>[0-5]\d)(?!\w)")
_ADDRESS_SUFFIX_RE = re.compile(
    r"(?<!\w)(?P<number>\d{1,4})(?P<suffix>[A-Za-z])\s+(?P<street>[A-ZÄÖÜ][\wÄÖÜäöüß.-]*(?:\s+(?:St\.?|Street|Ave\.?|Avenue|Rd\.?|Road|Blvd\.?))?)(?!\w)",
)
_ADDRESS_RE = re.compile(
    r"(?<!\w)(?P<street>(?:[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*(?:straße|strasse|platz|gasse|allee|weg|promenade)|[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*\s+(?:Street|St\.?|Road|Avenue|Ave\.?|Rd\.?|Blvd\.?)))\s+"
    r"(?P<number>\d{1,4})(?P<suffix>[A-Za-z])?(?:\s*[-–]\s*(?P<range>\d{1,4}))?(?:\s*/\s*(?P<slash>\d{1,4}))?(?!\w)",
    re.IGNORECASE,
)
_ADDRESS_REVERSE = re.compile(
    r"(?<!\w)(?P<number>\d{1,5})(?P<suffix>[A-Za-z])?\s+(?P<street>[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*)\s+"
    r"(?P<kind>Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?)(?!\w)",
    re.IGNORECASE,
)
_LEADING_ADDRESS_RE = re.compile(
    r"(?<!\w)(?P<number>\d{1,5})(?P<suffix>[A-Za-z])\s+(?P<street>[A-ZÀ-Ý][\wÀ-ÿ.-]*(?:\s+[A-ZÀ-Ý][\wÀ-ÿ.-]*){0,3})(?!\w)",
)
_ADDRESS_COMPONENT_RE = re.compile(
    r"(?P<label>Apt\.?|Apartment|Suite|Piso|Departamento|Interior|Local|Unité|Appartement|Tor|Einheit)\s*#?\s*(?P<number>\d+[A-Za-z]?)",
    re.IGNORECASE,
)
_POSTBOX_RE = re.compile(
    r"\b(?P<label>Postfach|P\.O\.\s*Box)\s+(?P<number>\d{1,6})\b", re.IGNORECASE
)
_FLOOR_RE = re.compile(r"(?<!\w)(?P<number>\d{1,2})\.\s*(?P<label>OG|Stockwerk)\b", re.IGNORECASE)
_POSTAL_CITY_RE = re.compile(
    r"(?<!\w)(?P<postal>\d{4,5})\s+(?P<city>[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ-]+)(?!\w)",
)
_ADDRESS_CONTEXT_RE = re.compile(
    r"(?<!\w)(?P<street>(?:Am|An\s+der|Auf\s+der|Im|In\s+der)\s+[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*)\s+"
    r"(?P<number>\d{1,4})(?P<suffix>[A-Za-z])?(?:\s*[-–]\s*(?P<range>\d{1,4}))?(?:\s*/\s*(?P<slash>\d{1,4}))?(?!\w)",
)
_POSTAL_CITY_NAMES = frozenset(
    {
        "Berlin",
        "Hamburg",
        "München",
        "Köln",
        "Frankfurt",
        "Stuttgart",
        "Dresden",
        "Leipzig",
        "Bremen",
        "Bonn",
        "Hannover",
        "Nürnberg",
        "Potsdam",
        "Wien",
        "Zürich",
    }
)

_FRACTIONS: dict[str, Fraction] = {
    "½": Fraction(1, 2),
    "⅓": Fraction(1, 3),
    "⅔": Fraction(2, 3),
    "¼": Fraction(1, 4),
    "¾": Fraction(3, 4),
    "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8),
    "⅝": Fraction(5, 8),
    "⅞": Fraction(7, 8),
    "⅕": Fraction(1, 5),
    "⅖": Fraction(2, 5),
    "⅗": Fraction(3, 5),
    "⅘": Fraction(4, 5),
    "⅙": Fraction(1, 6),
    "⅚": Fraction(5, 6),
}
_FRACTION_WORDS = {
    "en": {
        Fraction(1, 2): "one half",
        Fraction(1, 3): "one third",
        Fraction(2, 3): "two thirds",
        Fraction(1, 4): "one fourth",
        Fraction(3, 4): "three fourths",
        Fraction(1, 8): "one eighth",
        Fraction(3, 8): "three eighths",
        Fraction(5, 8): "five eighths",
        Fraction(7, 8): "seven eighths",
    },
    "de": {
        Fraction(1, 2): "einhalb",
        Fraction(1, 3): "ein Drittel",
        Fraction(2, 3): "zwei Drittel",
        Fraction(1, 4): "ein Viertel",
        Fraction(3, 4): "drei Viertel",
        Fraction(1, 8): "ein Achtel",
        Fraction(3, 8): "drei Achtel",
        Fraction(5, 8): "fünf Achtel",
        Fraction(7, 8): "sieben Achtel",
    },
    "es": {
        Fraction(1, 2): "un medio",
        Fraction(1, 3): "un tercio",
        Fraction(2, 3): "dos tercios",
        Fraction(1, 4): "un cuarto",
        Fraction(3, 4): "tres cuartos",
        Fraction(1, 8): "un octavo",
        Fraction(3, 8): "tres octavos",
        Fraction(5, 8): "cinco octavos",
        Fraction(7, 8): "siete octavos",
    },
    "fr": {
        Fraction(1, 2): "un demi",
        Fraction(1, 3): "un tiers",
        Fraction(2, 3): "deux tiers",
        Fraction(1, 4): "un quart",
        Fraction(3, 4): "trois quarts",
        Fraction(1, 8): "un huitième",
        Fraction(3, 8): "trois huitièmes",
        Fraction(5, 8): "cinq huitièmes",
        Fraction(7, 8): "sept huitièmes",
    },
    "it": {
        Fraction(1, 2): "un mezzo",
        Fraction(1, 3): "un terzo",
        Fraction(2, 3): "due terzi",
        Fraction(1, 4): "un quarto",
        Fraction(3, 4): "tre quarti",
        Fraction(1, 8): "un ottavo",
        Fraction(3, 8): "tre ottavi",
        Fraction(5, 8): "cinque ottavi",
        Fraction(7, 8): "sette ottavi",
    },
}
_DENOMINATOR_WORDS = {
    "en": {
        2: "half",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
        16: "sixteenth",
    },
    "de": {
        2: "halb",
        3: "Drittel",
        4: "Viertel",
        5: "Fünftel",
        6: "Sechstel",
        7: "Siebtel",
        8: "Achtel",
        9: "Neuntel",
        10: "Zehntel",
        16: "Sechzehntel",
    },
    "es": {
        2: "medio",
        3: "tercio",
        4: "cuarto",
        5: "quinto",
        6: "sexto",
        7: "séptimo",
        8: "octavo",
        9: "noveno",
        10: "décimo",
        16: "dieciseisavo",
    },
    "fr": {
        2: "demi",
        3: "tiers",
        4: "quart",
        5: "cinquième",
        6: "sixième",
        7: "septième",
        8: "huitième",
        9: "neuvième",
        10: "dixième",
        16: "seizième",
    },
    "it": {
        2: "mezzo",
        3: "terzo",
        4: "quarto",
        5: "quinto",
        6: "sesto",
        7: "settimo",
        8: "ottavo",
        9: "nono",
        10: "decimo",
        16: "sedicesimo",
    },
}
_ELEMENT_SYMBOLS = frozenset(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)
_GREEK_NAMES = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "ε": "epsilon",
    "θ": "theta",
    "λ": "lambda",
    "μ": "mu",
    "π": "pi",
    "σ": "sigma",
    "φ": "phi",
    "ω": "omega",
    "Δ": "Delta",
    "Σ": "Sigma",
    "Ω": "Omega",
}


@dataclass(frozen=True, slots=True)
class IsbnRenderPolicy:
    """Locale policy for rendering validated ISBN groups."""

    group_mode: Literal["digitwise", "cardinal"]
    label_mode: Literal["letters", "letters_and_kind"] = "letters"
    separator_word: str | None = None
    speak_group_boundaries: bool = False


@dataclass(frozen=True, slots=True)
class PhoneCandidate:
    """Parsed phone groups retained until locale rendering."""

    country_prefix: str | None
    groups: tuple[str, ...]
    punctuation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PhoneRenderPolicy:
    """Locale policy for phone plus signs, groups, and leading zeroes."""

    group_mode: Literal["digitwise", "two_digit_cardinal", "cardinal"]
    preserve_leading_zero: bool = True
    plus_word: str = "plus"


_PHONE_POLICIES = {
    "en": PhoneRenderPolicy("digitwise"),
    "de": PhoneRenderPolicy("digitwise"),
    "es": PhoneRenderPolicy("digitwise", plus_word="más"),
    "fr": PhoneRenderPolicy("two_digit_cardinal"),
    "it": PhoneRenderPolicy("digitwise", plus_word="più"),
}


@dataclass(frozen=True, slots=True)
class EmergencyNumberPolicy:
    """Locale/domain policy for emergency-number speech."""

    mode: Literal["digitwise", "cardinal"] = "cardinal"


_EMERGENCY_POLICIES = {
    "en": EmergencyNumberPolicy("cardinal"),
    "de": EmergencyNumberPolicy("cardinal"),
    "es": EmergencyNumberPolicy("digitwise"),
    "fr": EmergencyNumberPolicy("digitwise"),
    "it": EmergencyNumberPolicy("digitwise"),
}


@dataclass(frozen=True, slots=True)
class CodeToken:
    """One semantic token in an alphanumeric code."""

    kind: Literal["letters", "digits", "separator"]
    text: str


@dataclass(frozen=True, slots=True)
class CodeRenderPolicy:
    """Category-specific rendering policy for typed codes."""

    letters: Literal["grapheme", "spoken_letter_name", "lexical"] = "grapheme"
    digits: Literal["digitwise", "cardinal", "year"] = "digitwise"
    separators: Literal["omit", "speak", "segment"] = "omit"
    digit_mode: Literal["digits", "cardinal", "grouped", "mixed_product"] = "digits"


_CODE_POLICIES = {
    "serial": CodeRenderPolicy("grapheme", "digitwise", "omit", "digits"),
    "vin": CodeRenderPolicy("grapheme", "digitwise", "omit", "digits"),
    "license": CodeRenderPolicy("grapheme", "digitwise", "omit", "digits"),
    "model": CodeRenderPolicy("grapheme", "cardinal", "omit", "mixed_product"),
    "product": CodeRenderPolicy("grapheme", "digitwise", "omit", "digits"),
    "vehicle": CodeRenderPolicy("grapheme", "cardinal", "omit", "mixed_product"),
}


_ISBN_POLICIES = {
    "en": IsbnRenderPolicy("digitwise", "letters_and_kind"),
    "de": IsbnRenderPolicy("digitwise", "letters_and_kind"),
    "es": IsbnRenderPolicy("digitwise", "letters_and_kind", ", guión ", True),
    "it": IsbnRenderPolicy("digitwise", "letters_and_kind", ", ", True),
    "fr": IsbnRenderPolicy("cardinal", "letters_and_kind", ", ", True),
}


def _cardinal(value: int, language: str) -> str:
    rendered = str(number_words(value, lang=language))
    if base_language(language) == "en":
        return rendered.replace(" and ", " ")
    return rendered


def _quarter_text(quarter: int, language: str, year: int | None, fiscal_year: int | None) -> str:
    quarter_word = {
        "de": "Quartal",
        "es": "trimestre",
        "fr": "trimestre",
        "it": "trimestre",
        "pt": "trimestre",
        "cs": "čtvrtletí",
    }.get(base_language(language), "quarter")
    value = f"{quarter_word} {_cardinal(quarter, language).replace('-', ' ')}"
    if year is not None:
        value += f" {_cardinal(year, language).replace('-', ' ')}"
    if fiscal_year is not None:
        prefix = "fiscal year" if base_language(language) == "en" else "FY"
        value = f"{prefix} {_cardinal(fiscal_year, language).replace('-', ' ')} {value}"
    return value


def _digitwise(value: str, language: str) -> str:
    return render_sequence(value, language=language, digit_mode="digitwise")


def _punctuated(value: str, language: str) -> str:
    return render_sequence(value, language=language, digit_mode="digitwise")


def _mac_text(value: str, language: str) -> str:
    """Render MAC components while keeping colons silent."""
    parts: list[str] = []
    for group in re.split(r"[:-]", value):
        for token in re.findall(r"[A-Za-z]+|\d+", group):
            parts.append(
                _digitwise(token, language) if token.isdigit() else _grapheme_text(token, language)
            )
    return " ".join(part for part in parts if part)


def _ip_text(value: str, language: str) -> str:
    point = {"de": "Punkt", "es": "punto", "fr": "point", "it": "punto"}.get(
        base_language(language), "point"
    )
    return f" {point} ".join(_digitwise(part, language) for part in value.split("."))


def _fraction_text(whole: str | None, symbol: str, language: str) -> str:
    base = base_language(language)
    fraction = _FRACTIONS[symbol]
    fraction_text = _FRACTION_WORDS.get(base, _FRACTION_WORDS["en"]).get(fraction)
    if base == "es" and whole == "1" and fraction == Fraction(1, 2):
        fraction_text = "media"
    if base == "es" and whole == "1":
        whole_text = "Una"
    else:
        whole_text = _cardinal(int(whole), language) if whole is not None else ""
    if fraction_text is None:
        fraction_text = _fraction_word(fraction.numerator, fraction.denominator, language)
    if whole is None:
        return fraction_text
    connector = {"de": "und", "es": "y", "fr": "et", "it": "e"}.get(base, "and")
    return f"{whole_text} {connector} {fraction_text}"


def _fraction_word(numerator: int, denominator: int, language: str) -> str:
    """Render a slash fraction with explicit, locale-aware morphology."""
    base = base_language(language)
    words = _DENOMINATOR_WORDS.get(base, _DENOMINATOR_WORDS["en"])
    denominator_word = words.get(denominator)
    if denominator_word is None:
        denominator_word = str(number_words(denominator, lang=language, to="ordinal"))
    if base == "de":
        return f"{_cardinal(numerator, language)} {denominator_word}"
    if base == "fr":
        return f"{_cardinal(numerator, language)} {denominator_word}{'s' if numerator != 1 and not denominator_word.endswith('s') else ''}"
    if base == "es":
        article = "un" if numerator == 1 else _cardinal(numerator, language)
        suffix = "s" if numerator != 1 and not denominator_word.endswith("s") else ""
        return f"{article} {denominator_word}{suffix}"
    if base == "it":
        article = "un" if numerator == 1 else _cardinal(numerator, language)
        suffix = "i" if numerator != 1 and denominator_word.endswith("o") else ""
        return f"{article} {denominator_word[:-1] + suffix if suffix else denominator_word}"
    if denominator == 2:
        denominator_word = "half" if numerator == 1 else "halves"
    elif numerator != 1:
        denominator_word += "s" if not denominator_word.endswith("s") else ""
    return f"{_cardinal(numerator, language)} {denominator_word}"


def _slash_fraction_text(
    whole: str | None, numerator: str, denominator: str, language: str
) -> str | None:
    denominator_value = int(denominator)
    numerator_value = int(numerator)
    if denominator_value <= 0 or numerator_value <= 0 or denominator_value > 100:
        return None
    if (
        base_language(language) == "es"
        and whole is None
        and numerator_value == 1
        and denominator_value == 2
    ):
        return "medio"
    if (
        base_language(language) == "fr"
        and whole is None
        and numerator_value == 1
        and denominator_value == 2
    ):
        return "la moitié"
    if (
        base_language(language) == "fr"
        and whole is None
        and numerator_value == 1
        and denominator_value == 100
    ):
        return "un centième"
    if (
        base_language(language) == "it"
        and whole is None
        and numerator_value == 1
        and denominator_value == 2
    ):
        return "metà"
    fraction = _fraction_word(numerator_value, denominator_value, language)
    if (
        whole is not None
        and base_language(language) == "en"
        and numerator_value == 1
        and denominator_value == 2
    ):
        fraction = "a half"
    if (
        whole is not None
        and base_language(language) == "en"
        and numerator_value == 1
        and denominator_value == 4
    ):
        fraction = "a quarter"
    if whole is None:
        return fraction
    connector = {"de": "und", "es": "y", "fr": "et", "it": "e"}.get(base_language(language), "and")
    return f"{_cardinal(int(whole), language)} {connector} {fraction}"


def _coordinate_is_valid(value: str, direction: str | None) -> bool:
    try:
        numeric = abs(float(value.replace(",", ".")))
    except ValueError:
        return False
    if direction is None:
        return True
    limit = 90 if direction.upper() in {"N", "S"} else 180
    return numeric <= limit


def _coordinate_text(value: str, direction: str | None, language: str) -> str:
    lexeme = parse_numeric_lexeme(value, language, context="coordinate")
    if lexeme is None:
        return value
    integer, fraction = lexeme.integer_digits, lexeme.fraction_digits
    sign = "minus " if lexeme.negative else "plus " if value.startswith("+") else ""
    base = base_language(language)
    decimal_word = numeric_speech_policy(language).decimal_word
    direction_words = {
        "en": {"N": "north", "S": "south", "E": "east", "W": "west"},
        "de": {"N": "Nord", "S": "Süd", "E": "Ost", "W": "West"},
        "es": {"N": "norte", "S": "sur", "E": "este", "W": "oeste"},
        "fr": {"N": "nord", "S": "sud", "E": "est", "W": "ouest"},
        "it": {"N": "nord", "S": "sud", "E": "est", "W": "ovest"},
        "pt": {"N": "norte", "S": "sul", "E": "leste", "W": "oeste"},
        "cs": {"N": "sever", "S": "jih", "E": "východ", "W": "západ"},
    }.get(base_language(language), {"N": "north", "S": "south", "E": "east", "W": "west"})
    direction_words.setdefault("O", "oeste" if base == "es" else "west")
    degree = {
        "cs": "stupňů",
        "de": "Grad",
        "es": "grados",
        "fr": "degrés",
        "it": "gradi",
        "pt": "graus",
    }.get(base, "degrees")
    result = f"{sign}{_cardinal(int(integer), language)}"
    if fraction:
        result += f" {decimal_word} {_digitwise(fraction, language)}"
    result += f" {degree}"
    if direction:
        result += f" {direction_words[direction.upper()]}"
    return result


def _decimal_parts(
    raw: str, language: str, *, context: str = "plain"
) -> tuple[bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, language, context=context)
    if lexeme is None:
        raise ValueError(f"Cannot parse numeric lexeme {raw!r}")
    return lexeme.negative, int(lexeme.integer_digits or "0"), lexeme.fraction_digits


def _decimal_text(raw: str, language: str, *, context: str = "plain") -> str:
    negative, integer, fraction = _decimal_parts(raw, language, context=context)
    decimal_word = numeric_speech_policy(language).decimal_word
    value = _cardinal(integer, language)
    if fraction:
        groups = fraction_digit_groups(fraction, language)
        rendered_fraction = " ".join(
            _cardinal(int(group), language)
            if len(groups) < len(fraction)
            else _digitwise(group, language)
            for group in groups
        )
        value += f" {decimal_word} {rendered_fraction}"
    return f"minus {value}" if negative else value


def _percent_text(raw: str, language: str) -> str:
    names = {
        "cs": "procent",
        "de": "Prozent",
        "en": "percent",
        "es": "por ciento",
        "fr": "pour cent",
        "it": "percento",
        "pt": "por cento",
    }
    if base_language(language) == "es" and re.fullmatch(r"[+\-−]?\d+[.,]0+", raw.strip()):
        normalized = raw.strip().replace("−", "-")
        sign = "-" if normalized.startswith("-") else ""
        integer = normalized.lstrip("+-").split(".", 1)[0].split(",", 1)[0]
        number = _cardinal(int(f"{sign}{integer}"), language)
        return f"{number} {names['es']}"
    return f"{_decimal_text(raw, language, context='percent')} {names.get(base_language(language), 'percent')}"


def _currency_symbol_text(raw: str, symbol: str, language: str) -> str:
    base = base_language(language)
    names = {
        "€": {
            "de": "Euro",
            "en": "euro",
            "es": "euros",
            "fr": "euros",
            "it": "euro",
            "pt": "euros",
            "cs": "euro",
        },
        "$": {
            "de": "Dollar",
            "en": "dollar",
            "es": "dólares",
            "fr": "dollars",
            "it": "dollari",
            "pt": "dólares",
            "cs": "dolar",
        },
        "£": {
            "de": "Pfund",
            "en": "pounds",
            "es": "libras",
            "fr": "livres",
            "it": "sterline",
            "pt": "libras",
            "cs": "libry",
        },
    }
    minor_names = {
        "de": "Cent",
        "en": "cents",
        "es": "centavos",
        "fr": "centimes",
        "it": "centesimi",
        "pt": "centavos",
        "cs": "centů",
    }
    negative, integer, fraction = _decimal_parts(raw, language, context="currency")
    major = _cardinal(integer, language)
    if negative:
        major = f"minus {major}"
    currency_name = names[symbol].get(base, names[symbol]["en"])
    if base == "en" and (integer != 1 or fraction):
        currency_name += "s"
    result = f"{major} {currency_name}"
    if fraction:
        minor = int((fraction + "00")[:2])
        if minor:
            if base == "de":
                result += f" {_cardinal(minor, language)}"
            else:
                result += f" {('and' if base == 'en' else 'e' if base in {'it', 'pt'} else 'con')} {_cardinal(minor, language)} {minor_names.get(base, 'cents')}"
    return result


_CURRENCY_CODE_NAMES = {
    "EUR": {"en": "euro", "de": "Euro", "es": "euros", "fr": "euros", "it": "euro"},
    "USD": {
        "en": "US dollars",
        "de": "US-Dollar",
        "es": "dólares estadounidenses",
        "fr": "dollars américains",
        "it": "dollari statunitensi",
    },
    "GBP": {
        "en": "pounds",
        "de": "Pfund",
        "es": "libras esterlinas",
        "fr": "livres sterling",
        "it": "sterline",
    },
    "JPY": {"en": "yen", "de": "Yen", "es": "yenes", "fr": "yens", "it": "yen"},
    "CHF": {
        "en": "Swiss francs",
        "de": "Schweizer Franken",
        "es": "francos suizos",
        "fr": "francs suisses",
        "it": "franchi svizzeri",
    },
    "INR": {
        "en": "rupees",
        "de": "Indische Rupien",
        "es": "rupias",
        "fr": "roupies",
        "it": "rupie",
    },
    "KRW": {"en": "won", "de": "Won", "es": "wones", "fr": "wons", "it": "won"},
    "MXN": {
        "en": "Mexican pesos",
        "de": "Mexikanische Pesos",
        "es": "pesos mexicanos",
        "fr": "pesos mexicains",
        "it": "pesos messicani",
    },
}
_CURRENCY_SYMBOL_CODES = {"€": "EUR", "$": "USD", "£": "GBP"}


def _currency_code_text(number: str, code: str, language: str) -> str:
    canonical = _CURRENCY_SYMBOL_CODES.get(code, code.upper())
    name = _CURRENCY_CODE_NAMES.get(canonical, {}).get(base_language(language), canonical)
    return f"{_decimal_text(number, language, context='currency')} {name}"


def _compound_unit_text(number: str | None, unit: str, language: str) -> str:
    base = base_language(language)
    unit_key = re.sub(r"\s+", "", unit.casefold()).replace("3", "³")
    labels = {
        "g/cm³": {
            "en": "grams per cubic centimeter",
            "de": "Gramm pro Kubikzentimeter",
            "es": "gramos por centímetro cúbico",
            "fr": "grammes par centimètre cube",
            "it": "grammi per centimetro cubo",
            "pt": "gramas por centímetro cúbico",
            "cs": "gramů na centimetr krychlový",
        },
        "mol/l": {
            "en": "moles per liter",
            "de": "Mol pro Liter",
            "es": "moles por litro",
            "fr": "moles par litre",
            "it": "moli per litro",
            "pt": "moles por litro",
            "cs": "molů na litr",
        },
        "l/100km": {
            "en": "liters per one hundred kilometers",
            "de": "Liter pro hundert Kilometer",
            "es": "litros por cien kilómetros",
            "fr": "litres aux cent kilomètres",
            "it": "litri per cento chilometri",
            "pt": "litros por cem quilômetros",
            "cs": "litrů na sto kilometrů",
        },
    }
    label = labels[unit_key].get(base, labels[unit_key]["en"])
    return f"{_decimal_text(number, language, context='quantity')} {label}" if number else label


def _claimed(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return not any(start < right and left < end for left, right in protected)


def _phone_is_plausible(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if (
        re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", value)
        or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value)
        or re.fullmatch(r"\d{1,2}:\d{2}", value)
        or re.fullmatch(r"\d{4}-\d{4}", value)
        or ":" in value
        or "," in value
        or ("." in value and not re.fullmatch(r"\+?\d{2,4}(?:\.\d{2,4}){1,3}", value))
    ):
        return False
    return len(digits) >= 7 and (value.startswith("+") or bool(re.search(r"[ ()/.-]", value)))


def _phone_context(text: str, start: int, end: int, value: str) -> bool:
    context = f"{text[max(0, start - 48) : start]} {text[end : end + 24]}"
    if value.startswith("+"):
        return True
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 10 and re.search(r"[. ()/-]", value):
        return True
    return bool(
        re.search(
            r"\b(?:phone|telephone|tel|call|contact|text\s+me|support\s+line|mobile|fax|telefon|telefonnummer|teléfono|número\s+de\s+(?:teléfono|emergencia)|téléphone|numero\s+(?:di\s+)?(?:telefono|aziendale|di\s+casa)|centralino|servizio(?:\s+clienti)?)\b",
            context,
            re.IGNORECASE,
        )
    )


def _looks_like_date_shape(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}", value.strip()))


def _roman_value(value: str) -> int:
    weights = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for character in reversed(value.upper()):
        current = weights[character]
        total += -current if current < previous else current
        previous = max(previous, current)
    return total


def _roman_is_valid(value: str) -> bool:
    if not value or re.search(r"[^IVXLCDM]", value.upper()):
        return False
    canonical = ""
    remaining = _roman_value(value)
    for number, token in (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ):
        count, remaining = divmod(remaining, number)
        canonical += token * count
    return canonical == value.upper()


RomanSemantic = Literal["cardinal", "ordinal", "year", "monarch"]


def _roman_number_text(value: int, language: str, *, ordinal: bool = False) -> str:
    rendered = str(
        number_words(
            value,
            lang=language,
            to="ordinal" if ordinal else "cardinal",
        )
    )
    if base_language(language) == "en":
        return rendered.replace(",", "").replace("-", " ").replace(" and ", " ")
    return rendered


def _roman_monarch_text(value: int, language: str, context: str) -> str:
    base = base_language(language)
    if base == "fr":
        return _roman_number_text(value, language)
    ordinal = _roman_number_text(value, language, ordinal=True)
    if base == "en":
        return f"the {ordinal}"
    if base == "de":
        article = "die" if re.search(r"(?i:Elisabeth|Königin)", context) else "der"
        return f"{article} {ordinal[:1].upper()}{ordinal[1:]}"
    if base == "pt":
        return f"o {ordinal}"
    if base == "es":
        return f"el {ordinal}"
    return ordinal


def _roman_text(
    value: str,
    *,
    semantic: RomanSemantic,
    language: str,
    context: str | None = None,
) -> str:
    number = _roman_value(value)
    if semantic == "year":
        return render_year(number, language=language, source_digits=4)
    if semantic == "ordinal":
        return _roman_number_text(number, language, ordinal=True)
    if semantic == "monarch":
        return _roman_monarch_text(number, language, context or "")
    return _roman_number_text(number, language)


def _literal_tail(value: str) -> tuple[str, str]:
    """Split sentence punctuation from a typed literal without losing it."""
    body = value.rstrip(".,;:!?")
    return body, value[len(body) :]


def _literal_symbol_words(language: str) -> dict[str, str]:
    base = base_language(language)
    return {
        ".": {"de": "Punkt", "es": "punto", "fr": "point", "it": "punto"}.get(base, "dot"),
        "/": {"de": "Schrägstrich", "es": "barra", "fr": "barre oblique", "it": "barra"}.get(
            base, "slash"
        ),
        ":": {"de": "Doppelpunkt", "es": "dos puntos", "fr": "deux-points", "it": "due punti"}.get(
            base, "colon"
        ),
        "@": {"de": "at", "es": "arroba", "fr": "arobase", "it": "chiocciola"}.get(base, "at"),
        "?": {
            "de": "Fragezeichen",
            "es": "interrogación",
            "fr": "point d’interrogation",
            "it": "punto interrogativo",
        }.get(base, "question mark"),
        "&": {"de": "und", "es": "y", "fr": "et", "it": "e"}.get(base, "and"),
    }


def _url_text(
    value: str,
    language: str,
    *,
    evidence: EvidenceSession | None = None,
) -> str:
    """Render a URL while optionally using lexical evidence for host labels."""
    if evidence is None or not evidence.available:
        return _legacy_url_text(value, language)
    body, tail = _literal_tail(value)
    symbols = _literal_symbol_words(language)
    scheme, separator, remainder = body.partition("://")
    parsed = urlsplit(f"//{remainder if separator else body}")
    host = parsed.hostname
    if not host or parsed.netloc.casefold() != host.casefold():
        return _legacy_url_text(value, language)
    parts: list[str] = []
    if separator:
        parts.extend([_grapheme_text(scheme, language), symbols[":"], symbols["/"], symbols["/"]])
    parts.append(_url_hostname_text(host, language, evidence=evidence))
    suffix = parsed.path
    if parsed.query:
        suffix += f"?{parsed.query}"
    if parsed.fragment:
        suffix += f"#{parsed.fragment}"
    parts.extend(_url_tail_parts(suffix, language))
    return " ".join(part for part in parts if part) + tail


def _legacy_url_text(value: str, language: str) -> str:
    """Keep the provider-free URL renderer byte-for-byte compatible."""
    body, tail = _literal_tail(value)
    symbols = _literal_symbol_words(language)
    lexical_host_labels = frozenset({"example", "company", "com", "org", "net"})
    parts: list[str] = []
    scheme, separator, remainder = body.partition("://")
    if separator:
        parts.extend([_grapheme_text(scheme, language), symbols[":"], symbols["/"], symbols["/"]])
    else:
        remainder = body
    for chunk in re.split(r"([./?:&=])", remainder):
        if not chunk:
            continue
        if chunk in symbols:
            parts.append(symbols[chunk])
        elif chunk.isalnum() and chunk.casefold() in lexical_host_labels:
            parts.append(chunk)
        elif chunk.isalnum():
            parts.append(
                render_sequence(chunk, language=language)
                if any(character.isdigit() for character in chunk)
                else _grapheme_text(chunk, language)
            )
        else:
            parts.append(chunk)
    return " ".join(parts) + tail


def _url_tail_parts(value: str, language: str) -> list[str]:
    """Render non-host URL components with the established symbol policy."""
    symbols = _literal_symbol_words(language)
    parts: list[str] = []
    for chunk in re.split(r"([./?:&=])", value):
        if not chunk:
            continue
        if chunk in symbols:
            parts.append(symbols[chunk])
        elif chunk.isalnum():
            parts.append(
                render_sequence(chunk, language=language)
                if any(character.isdigit() for character in chunk)
                else _grapheme_text(chunk, language)
            )
        else:
            parts.append(chunk)
    return parts


def _url_hostname_text(
    host: str,
    language: str,
    *,
    evidence: EvidenceSession,
) -> str:
    labels = host.split(".")
    return " dot ".join(
        _url_host_label_text(
            label,
            language,
            evidence=evidence,
            is_tld=index == len(labels) - 1,
        )
        for index, label in enumerate(labels)
    )


def _url_host_label_text(
    label: str,
    language: str,
    *,
    evidence: EvidenceSession,
    is_tld: bool,
) -> str:
    lexical_labels = frozenset({"example", "company", "com", "org", "net"})
    if label.casefold() == "www":
        return _grapheme_text(label, language)
    if is_tld and len(label) == 2 and label.isalpha():
        return _grapheme_text(label, language)
    if label.casefold() in lexical_labels:
        return label
    if "-" in label:
        return " hyphen ".join(
            _url_host_label_text(part, language, evidence=evidence, is_tld=False)
            for part in label.split("-")
        )
    if any(character.isdigit() for character in label):
        return " ".join(
            render_sequence(part, language=language)
            if part.isdigit()
            else _url_host_label_text(part, language, evidence=evidence, is_tld=False)
            for part in re.split(r"(\d+)", label)
            if part
        )
    segments = evidence.segment(label)
    rendered: list[str] = []
    for segment in segments:
        if segment.known:
            rendered.append(segment.text)
            continue
        word = evidence.word(segment.text)
        if (
            word is not None
            and word.known
            and word.has_uppercase
            and not word.has_lowercase
            and not word.has_titlecase
        ):
            rendered.append(_grapheme_text(segment.text, language))
        elif word is not None and word.known:
            rendered.append(segment.text)
        elif len(segment.text) <= 3 and segment.text.isascii() and segment.text.isalpha():
            rendered.append(_grapheme_text(segment.text, language))
        else:
            rendered.append(segment.text)
    if rendered:
        return " ".join(rendered)
    return _grapheme_text(label, language) if len(label) <= 3 else label


def _email_text(value: str, language: str) -> str:
    """Render an e-mail address with lexical local/domain parts."""
    body, tail = _literal_tail(value)
    symbols = _literal_symbol_words(language)
    parts: list[str] = []
    for _index, chunk in enumerate(re.split(r"([.@+_-])", body)):
        if not chunk:
            continue
        if chunk in symbols:
            parts.append(symbols[chunk])
        elif chunk in {"+", "_", "-"}:
            parts.append({"+": "plus", "_": "underscore", "-": "hyphen"}[chunk])
        else:
            parts.append(chunk)
    return " ".join(parts) + tail


def _version_text(
    value: str,
    language: str,
    *,
    include_version_word: bool | None = None,
) -> str:
    """Render version components while preserving zeroes and release suffixes."""
    body, tail = _literal_tail(value)
    has_v = body[:1].casefold() == "v"
    if include_version_word is None:
        include_version_word = has_v
    if has_v:
        body = body[1:]
    parts: list[str] = []
    if has_v and not include_version_word:
        parts.append(_grapheme_text("v", language))
    if include_version_word:
        parts.append(
            {"de": "Version", "es": "versión", "fr": "version", "it": "version"}.get(
                base_language(language), "version"
            )
        )
    for component in re.split(r"[.-]", body):
        if not component:
            continue
        suffix = re.fullmatch(r"([A-Za-z]+)(\d*)", component)
        if suffix:
            parts.append(_grapheme_text(suffix.group(1), language))
            if suffix.group(2):
                parts.append(_cardinal(int(suffix.group(2)), language))
        elif component.isdigit():
            parts.append(_cardinal(int(component), language))
        else:
            parts.append(render_sequence(component, language=language))
    point = _literal_symbol_words(language)["."]
    if has_v and not include_version_word and parts:
        rendered = f"{parts[0]} " + f" {point} ".join(parts[1:])
    elif include_version_word and parts:
        rendered = f"{parts[0]} " + f" {point} ".join(parts[1:])
    else:
        rendered = f" {point} ".join(parts) if parts else body
    return rendered + tail


def _phone_text(value: str, language: str) -> str:
    """Render phone groups without speaking ordinary separator punctuation."""
    policy = _PHONE_POLICIES.get(base_language(language), _PHONE_POLICIES["en"])
    groups = tuple(re.findall(r"\d+", value))
    rendered: list[str] = []
    if value.lstrip().startswith("+"):
        rendered.append(policy.plus_word)
    for index, group in enumerate(groups):
        if (
            policy.preserve_leading_zero
            and group.startswith("0")
            and not (base_language(language) == "es" and len(group) == 3)
        ):
            rendered.append(_digitwise(group, language))
        elif policy.group_mode == "cardinal" or (
            base_language(language) == "es"
            and (index == 0 and (len(group) == 3 or value.lstrip().startswith("+")))
        ):
            rendered.append(_cardinal(int(group), language))
        elif policy.group_mode == "two_digit_cardinal" and len(group) == 2:
            rendered.append(_cardinal(int(group), language))
        else:
            rendered.append(_digitwise(group, language))
    separator = ", " if base_language(language) in {"es", "fr", "it"} and len(groups) > 1 else " "
    return separator.join(rendered)


def _marker_text(marker: str, value: str, language: str, *, include_marker: bool = True) -> str:
    marker_words = {
        "#": {
            "cs": "hashtag",
            "de": "Hashtag",
            "en": "hashtag",
            "es": "hashtag",
            "fr": "hashtag",
            "it": "hashtag",
            "pt": "hashtag",
        },
        "@": {
            "cs": "zavináč",
            "de": "at",
            "en": "at",
            "es": "arroba",
            "fr": "arobase",
            "it": "chiocciola",
            "pt": "arroba",
        },
    }
    marker_name = marker_words[marker].get(base_language(language), marker)
    rendered = _render_identifier(value, language, marker=marker)
    return f"{marker_name} {rendered}" if include_marker else rendered


def _identifier_tokens(value: str) -> tuple[tuple[str, str], ...]:
    """Split a social identifier at words, case, digits, and separators."""
    tokens: list[tuple[str, str]] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            token = "".join(current)
            kind = "digit" if token[0].isdigit() else "alpha"
            tokens.append((kind, token))
            current.clear()

    for index, character in enumerate(value):
        if character in "_-":
            flush()
            tokens.append(("separator", character))
            continue
        if character.isspace():
            flush()
            tokens.append(("separator", " "))
            continue
        if current and character.isdigit() != current[-1].isdigit():
            flush()
        elif current and character.isupper() and current[-1].islower():
            flush()
        elif (
            current
            and character.isupper()
            and current[-1].isupper()
            and index + 1 < len(value)
            and value[index + 1].islower()
        ):
            flush()
        current.append(character)
    flush()
    return tuple(tokens)


def _render_identifier(value: str, language: str, *, marker: str | None = None) -> str:
    """Render lexical social identifiers without spelling ordinary words."""
    tokens = _identifier_tokens(value)
    alpha = "".join(token for kind, token in tokens if kind == "alpha")
    opaque = bool(alpha) and alpha.isascii() and alpha.isupper() and len(alpha) <= 8
    rendered: list[str] = []
    separator_modes = {
        "#": {"_": "space", "-": "space"},
        "@": {"_": "space", "-": "space"},
    }
    for index, (kind, token) in enumerate(tokens):
        if kind == "digit":
            if len(token) == 4 and 1900 <= int(token) <= 2100:
                if base_language(language) == "en":
                    rendered.append(render_english_year(int(token), language=language))
                else:
                    rendered.append(_cardinal(int(token), language))
            elif any(
                adjacent_kind == "alpha" and not adjacent_token.isupper()
                for adjacent_kind, adjacent_token in (
                    tokens[index - 1] if index else ("", ""),
                    tokens[index + 1] if index + 1 < len(tokens) else ("", ""),
                )
            ):
                rendered.append(_cardinal(int(token), language))
            else:
                rendered.append(_digitwise(token, language))
        elif kind == "separator":
            mode = separator_modes.get(marker or "", {}).get(token, "speak")
            if mode == "drop":
                continue
            if mode == "space":
                rendered.append("")
            else:
                rendered.append(
                    (
                        vocabulary(language).underscore
                        if token == "_"
                        else vocabulary(language).hyphen
                    )
                    or token
                )
        elif (
            opaque
            and token.isascii()
            and token.isupper()
            and (len(token) > 1 or (marker == "#" and base_language(language) == "en"))
        ):
            rendered.append(render_letters(token, language=language))
        else:
            rendered.append(token)
    return " ".join(part for part in rendered if part)


def _formula_is_plausible(value: str) -> bool:
    # Mixed-case plural initialisms such as IDs, PCs, and ICs can accidentally
    # segment into valid element symbols (I + Ds, P + Cs, I + Cs). Prefer
    # ordinary-language safety for this ambiguous shape.
    if re.fullmatch(r"[A-Z]{2,8}s", value):
        return False

    tokens = re.findall(r"[A-Z][a-z]?", value)
    if value.count("(") != value.count(")") or value.find(")") < value.find("("):
        return False
    return (
        all(token in _ELEMENT_SYMBOLS for token in tokens)
        and (len(tokens) >= 2 or bool(re.search(r"[0-9₀-₉]", value)))
        and bool(re.search(r"[a-z]", value) or re.search(r"[0-9₀-₉]", value))
    )


def _formula_context_is_balanced(text: str, start: int, end: int) -> bool:
    """Do not salvage a formula fragment from an unmatched parenthesized span."""
    before = text[:start]
    after = text[end:]
    return before.count("(") == before.count(")") and after.count(")") == after.count("(")


def _isbn_shape_is_valid(value: str) -> bool:
    compact = re.sub(r"[-\s]", "", value).upper()
    if len(compact) == 10 and re.fullmatch(r"\d{9}[\dX]", compact):
        return True
    if len(compact) == 13 and compact.isdigit():
        return True
    return False


def _isbn_is_valid(value: str) -> bool:
    """Return checksum validity for diagnostics, not explicit-label ownership."""
    compact = re.sub(r"[-\s]", "", value).upper()
    if not _isbn_shape_is_valid(value):
        return False
    if len(compact) == 10:
        return (
            sum(
                (10 - index) * (10 if digit == "X" else int(digit))
                for index, digit in enumerate(compact)
            )
            % 11
            == 0
        )
    return (
        sum((1 if index % 2 == 0 else 3) * int(digit) for index, digit in enumerate(compact)) % 10
        == 0
    )


def _formula_text(value: str, language: str) -> str:
    parts: list[str] = []
    for match in re.finditer(r"[A-Z][a-z]?|[()]|[0-9₀-₉]+", value):
        token = match.group(0)
        if token.isdigit() or any(character in "₀₁₂₃₄₅₆₇₈₉" for character in token):
            parts.append(
                _cardinal(int(token.translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))), language)
            )
        elif token in "()":
            parts.append(
                (
                    vocabulary(language).open_paren
                    if token == "("
                    else vocabulary(language).close_paren
                )
                or token
            )
        else:
            parts.extend(token)
    return " ".join(parts)


def _math_text(value: str, language: str) -> str:
    operators = {
        "en": {
            "+": "plus",
            "−": "minus",
            "-": "minus",
            "*": "times",
            "×": "times",
            "÷": "divided by",
            "=": "equals",
            "<": "less than",
            ">": "greater than",
            "^": "to the power of",
            "/": "over",
            "≈": "is approximately",
            "≠": "does not equal",
            "≤": "less than or equal to",
            "≥": "greater than or equal to",
        },
        "de": {
            "+": "plus",
            "−": "minus",
            "-": "minus",
            "*": "mal",
            "×": "mal",
            "÷": "geteilt durch",
            "=": "gleich",
            "<": "kleiner als",
            ">": "größer als",
            "^": "hoch",
            "/": "durch",
            "≈": "ist ungefähr gleich",
            "≠": "ist nicht gleich",
            "≤": "kleiner oder gleich",
            "≥": "größer oder gleich",
        },
        "es": {
            "+": "más",
            "−": "menos",
            "-": "menos",
            "*": "por",
            "×": "por",
            "÷": "dividido por",
            "=": "igual a",
            "<": "menor que",
            ">": "mayor que",
            "^": "elevado a",
            "/": "sobre",
            "≈": "aproximadamente igual a",
            "≠": "no es igual a",
            "≤": "menor o igual que",
            "≥": "mayor o igual que",
        },
        "fr": {
            "+": "plus",
            "−": "moins",
            "-": "moins",
            "*": "fois",
            "×": "fois",
            "÷": "divisé par",
            "=": "égal",
            "<": "inférieur à",
            ">": "supérieur à",
            "^": "puissance",
            "/": "sur",
            "≈": "est approximativement égal à",
            "≠": "n'est pas égal à",
            "≤": "inférieur ou égal à",
            "≥": "supérieur ou égal à",
        },
        "it": {
            "+": "più",
            "−": "meno",
            "-": "meno",
            "*": "per",
            "×": "per",
            "÷": "diviso per",
            "=": "uguale",
            "<": "minore di",
            ">": "maggiore di",
            "^": "alla potenza di",
            "/": "fratto",
            "≈": "approssimativamente uguale a",
            "≠": "non è uguale a",
            "≤": "minore o uguale a",
            "≥": "maggiore o uguale a",
        },
    }.get(base_language(language), {})
    parts: list[str] = []
    roots = {
        "en": "square root of",
        "de": "Quadratwurzel aus",
        "es": "raíz cuadrada de",
        "fr": "racine carrée de",
        "it": "radice quadrata di",
    }
    absolute_open = True
    tokens = re.findall(
        r"\d+(?:[.,]\d+)?|[A-Za-z]+|[α-ωΑ-Ω]|√|[|()]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+|[+−*=×÷<>^\-/≈≠≤≥]",
        value,
    )
    for _index, token in enumerate(tokens):
        if token.isascii() and token.isdigit():
            parts.append(_cardinal(int(token), language))
        elif re.fullmatch(r"\d+[.,]\d+", token):
            parts.append(_decimal_text(token, language, context="math"))
        elif token == "√":
            parts.append(roots.get(base_language(language), roots["en"]))
        elif token == "π":
            parts.append(
                {"de": "pi", "es": "pi", "fr": "pi", "it": "pi"}.get(base_language(language), "pi")
            )
        elif token == "Δ":
            parts.append(
                {"de": "Delta", "es": "delta", "fr": "delta", "it": "delta"}.get(
                    base_language(language), "delta"
                )
            )
        elif token in _GREEK_NAMES:
            parts.append(_GREEK_NAMES[token])
        elif token == "|":
            parts.append(
                {
                    "en": "absolute value of" if absolute_open else "absolute value",
                    "de": "Betrag von" if absolute_open else "Betrag",
                    "es": "valor absoluto de" if absolute_open else "valor absoluto",
                    "fr": "valeur absolue de" if absolute_open else "valeur absolue",
                    "it": "valore assoluto di" if absolute_open else "valore assoluto",
                }.get(
                    base_language(language),
                    "absolute value of" if absolute_open else "absolute value",
                )
                if absolute_open
                else ""
            )
            absolute_open = not absolute_open
        elif token in "()":
            parts.append(
                (
                    vocabulary(language).open_paren
                    if token == "("
                    else vocabulary(language).close_paren
                )
                or token
            )
        elif token in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            exponent = int(token.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")))
            if exponent == 2:
                parts.append(
                    {
                        "de": "zum Quadrat",
                        "es": "al cuadrado",
                        "fr": "au carré",
                        "it": "al quadrato",
                    }.get(base_language(language), "squared")
                )
            elif exponent == 3:
                parts.append(
                    {"de": "hoch drei", "es": "al cubo", "fr": "au cube", "it": "al cubo"}.get(
                        base_language(language), "cubed"
                    )
                )
            else:
                parts.append(
                    f"{operators.get('^', 'to the power of')} {_cardinal(exponent, language)}"
                )
        elif token.isalpha():
            parts.append(render_letters(token, language=language) if len(token) <= 2 else token)
        else:
            parts.append(operators[token])
    return " ".join(part for part in parts if part)


def _math_is_plausible(value: str, text: str, start: int) -> bool:
    """Require mathematical context before treating code hyphens as minus."""
    if (
        re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+", value)
        or re.fullmatch(r"\d+\s*/\s*\d+", value)
        or re.fullmatch(r"\d{1,4}/\d{1,2}/\d{1,4}", value)
    ):
        return False
    if re.fullmatch(r"[A-Za-z]{2,}\s*[-−]\s*[A-Za-z]{2,}", value):
        return False
    if re.fullmatch(r"[A-Za-z]{2,}\s*/\s*[A-Za-z]{2,}", value):
        return False
    if re.fullmatch(r"[A-Za-z]{1,4}\s*/\s*[A-Za-z]{1,4}", value):
        return False
    if re.fullmatch(r"[A-Za-z0-9._-]+\s*/\s*[A-Za-z0-9._-]+", value):
        return False
    prefix = text[max(0, start - 48) : start]
    if re.search(
        r"\b(?:phone|telephone|tel|call|contact|mobile|fax|telefon|teléfono|téléphone|telefono)\b",
        prefix,
        re.IGNORECASE,
    ) and re.search(r"\+?\d[\d ()/.-]{5,}\d", value):
        return False
    if re.search(
        r"\b(?:serial|sku|model|product|part|code|id|matricola|plate)\s*[:#-]?\s*$",
        prefix,
        re.IGNORECASE,
    ):
        return False
    return bool(re.search(r"[+*=×÷<>^/≈≠≤≥]|\s[-−]\s", value))


def _music_text(value: str, language: str) -> str:
    match = re.fullmatch(r"([A-Ga-g])([#b♯♭])?(.*)", value)
    if match is None:
        return value
    note = (
        match.group(1).upper()
        if base_language(language) == "de"
        else render_letters(match.group(1), language=language)
    )
    accidental_words = {
        "en": {"#": "sharp", "♯": "sharp", "b": "flat", "♭": "flat"},
        "de": {"#": "is", "♯": "is", "b": "B", "♭": "B"},
        "es": {"#": "sostenido", "♯": "sostenido", "b": "bemol", "♭": "bemol"},
        "fr": {"#": "dièse", "♯": "dièse", "b": "bémol", "♭": "bémol"},
        "it": {"#": "diesis", "♯": "diesis", "b": "bemolle", "♭": "bemolle"},
    }
    accidental = accidental_words.get(base_language(language), accidental_words["en"]).get(
        match.group(2), ""
    )
    suffix = match.group(3).lstrip("-")
    if suffix.casefold() == "dur":
        suffix = "Dur"
    elif suffix.casefold() == "moll":
        suffix = "Moll"
    elif suffix.isdigit():
        suffix = _cardinal(int(suffix), language)
    return " ".join(part for part in (note, accidental, suffix) if part)


def _biology_text(value: str, language: str) -> str:
    match = re.fullmatch(r"([A-Z])\.\s*([a-z][a-z-]+)(.*)", value)
    if match is None:
        return value
    suffix = match.group(3).strip()
    suffix = re.sub(
        r"\b(strain|variant|group)\s+([A-Za-z0-9-]+)",
        lambda item: (
            f"{item.group(1)} {_typed_code_text(item.group(2), language, category='model')}"
        ),
        suffix,
        flags=re.IGNORECASE,
    )
    return " ".join(
        part
        for part in (render_letters(match.group(1), language=language), match.group(2), suffix)
        if part
    )


def _grapheme_text(value: str, language: str) -> str:
    return render_sequence(
        value,
        language=language,
        policy=SequenceRenderPolicy(alpha_mode="grapheme_spaced"),
    )


def _biology_is_plausible(value: str, text: str, start: int) -> bool:
    """Reject dotted abbreviations whose following word only looks species-like."""
    prefix = text[max(0, start - 16) : start]
    species = value.split(maxsplit=1)[-1].casefold().split()[0]
    if species in _BIOLOGY_NON_SPECIES_WORDS:
        return False
    if re.match(r"(?:m|mme|z|dr|etc)\.\s", value, re.IGNORECASE):
        return False
    return not bool(re.search(r"(?:\bz|\bm|\bmme|\bdr|\betc)\.\s*$", prefix, re.IGNORECASE))


def _code_tokens(value: str) -> tuple[CodeToken, ...]:
    return tuple(
        CodeToken(
            "digits" if token.isdigit() else "letters" if token.isalpha() else "separator",
            token,
        )
        for token in re.findall(r"[A-Za-z]+|\d+|[^A-Za-z\d]+", value)
    )


def _typed_code_text(
    value: str,
    language: str,
    *,
    category: str = "product",
    policy: CodeRenderPolicy | None = None,
) -> str:
    policy = policy or _CODE_POLICIES.get(category, _CODE_POLICIES["product"])
    parts: list[str] = []
    for token in _code_tokens(value):
        if token.kind == "digits":
            if policy.digits == "cardinal" or (
                category == "product" and base_language(language) == "de" and len(value) <= 4
            ):
                parts.append(_cardinal(int(token.text), language))
            elif policy.digits == "year" and len(token.text) == 4:
                parts.append(_cardinal(int(token.text), language))
            else:
                parts.append(_digitwise(token.text, language))
        elif token.kind == "letters":
            if policy.letters == "lexical":
                parts.append(token.text)
            elif policy.letters == "grapheme":
                parts.append(_grapheme_text(token.text, language))
            else:
                parts.append(render_letters(token.text, language=language))
        elif policy.separators == "speak":
            parts.append(render_sequence(token.text, language=language))
        elif policy.separators == "segment":
            parts.append(SEGMENT_BOUNDARY)
    return " ".join(part for part in parts if part.strip())


def _ticker_text(value: str, language: str) -> str:
    """Render a typed market symbol as source graphemes."""
    return _grapheme_text(value, language)


def _isbn_text(value: str, language: str) -> str:
    """Render ISBN groups without speaking source hyphens."""
    policy = _ISBN_POLICIES.get(base_language(language), _ISBN_POLICIES["en"])
    groups = tuple(group for group in re.split(r"[-\s]+", value.strip()) if group)
    rendered: list[str] = []
    for group in groups:
        if policy.group_mode == "cardinal" and group.isdigit():
            rendered.append(_cardinal(int(group), language))
        else:
            rendered.append(_digitwise(group, language))
    separator = policy.separator_word or ""
    if policy.speak_group_boundaries and separator:
        return separator.join(rendered)
    return " ".join(rendered)


def _isbn_label_text(label: str, language: str) -> str:
    policy = _ISBN_POLICIES.get(base_language(language), _ISBN_POLICIES["en"])
    match = re.fullmatch(r"ISBN(?:-(10|13))?", label, re.IGNORECASE)
    if match is None or policy.label_mode == "letters":
        return _grapheme_text("ISBN", language)
    kind = match.group(1)
    if kind is None:
        return _grapheme_text("ISBN", language)
    words = {
        "en": {"10": "ten", "13": "thirteen"},
        "de": {"10": "zehn", "13": "dreizehn"},
        "es": {"10": "diez", "13": "trece"},
        "fr": {"10": "dix", "13": "treize"},
        "it": {"10": "dieci", "13": "tredici"},
    }
    return f"{_grapheme_text('ISBN', language)} {words.get(base_language(language), words['en'])[kind]}"


def _score_text(value: str, language: str) -> str:
    match = re.fullmatch(r"\s*(\d+)\s*(?::|[-–]|a|to|à)\s*(\d+)\s*", value, re.IGNORECASE)
    if match is None:
        return value
    left, right = match.groups()
    connector = {"de": "zu", "es": "a", "fr": "à", "it": "a"}.get(base_language(language), "to")
    return f"{_cardinal(int(left), language)} {connector} {_cardinal(int(right), language)}"


def _has_sports_context(
    text: str,
    start: int,
    end: int | None = None,
    *,
    evidence: EvidenceSession | None = None,
) -> bool:
    """Return whether local or provider evidence supports a sports context."""
    prefix = text[max(0, start - 64) : start]
    if _SPORTS_CONTEXT_RE.search(prefix):
        return True
    if evidence is None or not evidence.available or end is None:
        return False
    return evidence.supports(text, target=(start, end), domain="sports") is not None


def _chained_score_is_plausible(
    text: str,
    start: int,
    end: int,
    *,
    evidence: EvidenceSession | None = None,
) -> bool:
    """Require positive sports context for a three-or-more-part chain."""
    return _has_sports_context(text, start, end, evidence=evidence)


def _score_is_plausible(
    value: str,
    text: str,
    start: int,
    end: int,
    *,
    evidence: EvidenceSession | None = None,
) -> bool:
    """Use sports context for scores and positive provider corroboration."""
    if _has_sports_context(text, start, end, evidence=evidence):
        return True
    match = re.fullmatch(r"\s*(\d{1,2})\s*([:\-–])\s*(\d{1,2})\s*", value)
    return bool(
        match
        and match[2] == ":"
        and len(match[1]) == 1
        and len(match[3]) == 1
        and int(match[1]) <= 9
        and int(match[3]) <= 9
    )


def _duration_text(hour: str, minute: str, second: str, language: str) -> str:
    base = base_language(language)
    labels = {
        "en": ("hour", "hours", "minute", "minutes", "second", "seconds"),
        "de": ("Stunde", "Stunden", "Minute", "Minuten", "Sekunde", "Sekunden"),
        "es": ("hora", "horas", "minuto", "minutos", "segundo", "segundos"),
        "fr": ("heure", "heures", "minute", "minutes", "seconde", "secondes"),
        "it": ("ora", "ore", "minuto", "minuti", "secondo", "secondi"),
    }.get(base, ("hour", "hours", "minute", "minutes", "second", "seconds"))
    values = (int(hour), int(minute), int(second))
    result: list[str] = []
    for value, singular, plural in zip(values, labels[::2], labels[1::2], strict=True):
        result.append(f"{_cardinal(value, language)} {singular if value == 1 else plural}")
    return " ".join(result)


_LEGAL_LABEL_HEADINGS = {
    "de": {
        "section": "Abschnitt",
        "sec": "Abschnitt",
        "article": "Artikel",
        "art": "Artikel",
        "chapter": "Kapitel",
        "chap": "Kapitel",
    },
    "es": {
        "section": "sección",
        "sec": "sección",
        "article": "artículo",
        "art": "artículo",
        "chapter": "capítulo",
        "chap": "capítulo",
    },
    "fr": {
        "section": "section",
        "sec": "section",
        "article": "article",
        "art": "article",
        "chapter": "chapitre",
        "chap": "chapitre",
    },
    "it": {
        "section": "sezione",
        "sec": "sezione",
        "article": "articolo",
        "art": "articolo",
        "chapter": "capitolo",
        "chap": "capitolo",
    },
}
_LEGAL_GENERIC_HEADINGS = {
    "cs": ("paragraf", "článek"),
    "de": ("Paragraf", "Artikel"),
    "en": ("section", "article"),
    "es": ("párrafo", "artículo"),
    "fr": ("paragraphe", "article"),
    "it": ("paragrafo", "articolo"),
    "pt": ("parágrafo", "artigo"),
}
_LEGAL_LABELED_VALUE_RE = re.compile(
    r"(section|sec\.?|article|art\.?|chapter|chap\.?)\s*(\d+)(?:\s+(?:subsection|paragraph|para\.?|§)\s*(\d+))?",
    re.IGNORECASE,
)
_LEGAL_GERMAN_PARAGRAPH_VALUE_RE = re.compile(
    r"§\s*(\d+)(?:\s+Abs\.?\s*(\d+))?\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{1,})",
)
_LEGAL_GERMAN_ARTICLE_VALUE_RE = re.compile(
    r"(?:Art\.?|Artikel)\s*(\d+)\s+Abs\.?\s*(\d+)\s+([A-ZÄÖÜ]{2,})",
    re.IGNORECASE,
)
_LEGAL_GERMAN_ROMAN_VALUE_RE = re.compile(
    r"§\s*(\d+)\s+([IVXLCDM]+)(?:\s+(\d+))?\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{1,})",
)
_LEGAL_US_VALUE_RE = re.compile(r"(\d+)\s+U\.S\.C\.\s+§\s*(\d+)", re.IGNORECASE)
_LEGAL_ES_VALUE_RE = re.compile(r"ley\s+(\d{1,3}(?:\.\d{3})?)", re.IGNORECASE)
_LEGAL_IT_VALUE_RE = re.compile(r"legge\s+n\.?\s*(\d+)(?:/(\d{4}))?", re.IGNORECASE)
_LEGAL_ES_SLASH_VALUE_RE = re.compile(r"(sentencia|registro)\s+(\d+)/(\d{4})", re.IGNORECASE)
_LEGAL_IT_SLASH_VALUE_RE = re.compile(
    r"(legge|sentenza|regolamento)\s+(?:n\.?\s*)?(\d+)/(\d{3,4})", re.IGNORECASE
)
_LEGAL_DOCKET_VALUE_RE = re.compile(r"(Docket|Case)\s+No\.?\s*(.+)", re.IGNORECASE)
_LEGAL_FR_VALUE_RE = re.compile(r"(?:décret|decret)\s+n[°o]?\s*(\d{4})-(\d+)", re.IGNORECASE)
_LEGAL_PREFIX_VALUE_RE = re.compile(
    r"([A-ZÄÖÜ]{2,})\s+§\s*(\d+)(?:\s+Abs\.?\s*(\d+))?", re.IGNORECASE
)
_LEGAL_GENERIC_VALUE_RE = re.compile(
    r"(?:§|Art\.?|Artikel)\s*(\d+)(?:\s+([IVXLCDM]+))?(?:\s+(\d+))?\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{1,})$",
    re.IGNORECASE,
)


def _render_labeled_legal(value: str, language: str) -> str | None:
    match = _LEGAL_LABELED_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    base = base_language(language)
    key = match.group(1).casefold().rstrip(".")
    heading = _LEGAL_LABEL_HEADINGS.get(base, {}).get(key, key)
    result = f"{heading} {_cardinal(int(match.group(2)), language)}"
    if match.group(3):
        result += f" {_cardinal(int(match.group(3)), language)}"
    return result


def _render_german_paragraph(value: str, language: str) -> str | None:
    match = _LEGAL_GERMAN_PARAGRAPH_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    result = f"Paragraf {_cardinal(int(match.group(1)), language)}"
    if match.group(2):
        result += f" Absatz {_cardinal(int(match.group(2)), language)}"
    return f"{result} {render_sequence(match.group(3), language=language)}"


def _render_german_article(value: str, language: str) -> str | None:
    if base_language(language) != "de":
        return None
    match = _LEGAL_GERMAN_ARTICLE_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    return (
        f"Artikel {_cardinal(int(match.group(1)), language)} Absatz "
        f"{_cardinal(int(match.group(2)), language)} "
        f"{render_sequence(match.group(3), language=language)}"
    )


def _render_german_roman(value: str, language: str) -> str | None:
    match = _LEGAL_GERMAN_ROMAN_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    result = (
        f"Paragraf {_cardinal(int(match.group(1)), language)} "
        f"Absatz {_cardinal(_roman_value(match.group(2)), language)}"
    )
    if match.group(3):
        result += f" Satz {_cardinal(int(match.group(3)), language)}"
    return f"{result} {render_sequence(match.group(4), language=language)}"


def _render_us_code(value: str, language: str) -> str | None:
    match = _LEGAL_US_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    left = _cardinal(int(match.group(1)), language).replace("-", " ").replace(",", "")
    right = _cardinal(int(match.group(2)), language).replace("-", " ").replace(",", "")
    return f"{left} U S C section {right}"


def _render_spanish_law(value: str, language: str) -> str | None:
    match = _LEGAL_ES_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    return f"ley {_cardinal(int(match.group(1).replace('.', '')), language)}"


def _render_italian_law(value: str, language: str) -> str | None:
    match = _LEGAL_IT_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    result = f"legge numero {_cardinal(int(match.group(1)), language)}"
    if match.group(2):
        result += f" del {_cardinal(int(match.group(2)), language)}"
    return result


def _render_spanish_slash_reference(value: str, language: str) -> str | None:
    if base_language(language) != "es":
        return None
    match = _LEGAL_ES_SLASH_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    return (
        f"{match.group(1).casefold()} {_cardinal(int(match.group(2)), language)} de "
        f"{_cardinal(int(match.group(3)), language)}"
    )


def _render_italian_slash_reference(value: str, language: str) -> str | None:
    if base_language(language) != "it":
        return None
    match = _LEGAL_IT_SLASH_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    label = {
        "legge": "legge",
        "sentenza": "sentenza",
        "regolamento": "regolamento numero",
    }[match.group(1).casefold()]
    return (
        f"{label} {_cardinal(int(match.group(2)), language)} del "
        f"{_cardinal(int(match.group(3)), language)}"
    )


def _render_docket_piece(piece: str, language: str) -> str:
    if piece == ":":
        return "colon"
    if piece == "-":
        return "dash"
    if not piece.isdigit():
        return _grapheme_text(piece, language)
    if len(piece) == 4:
        return render_english_year(int(piece), language=language, source_digits=4)
    if len(piece) <= 2:
        return _cardinal(int(piece), language).replace("-", " ")
    return _digitwise(piece, language)


def _render_english_docket(value: str, language: str) -> str | None:
    if base_language(language) != "en":
        return None
    match = _LEGAL_DOCKET_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    label = "Docket Number" if match.group(1).casefold() == "docket" else "Case Number"
    identifier = match.group(2)
    if ":" in identifier:
        pieces = re.split(r"([:\-])", identifier)
        return f"{label} {' '.join(_render_docket_piece(piece, language) for piece in pieces)}"
    year, suffix = identifier.split("-", 1)
    return f"{label} {render_english_year(int(year), language=language, source_digits=4)} dash {_digitwise(suffix, language)}"


def _render_french_decree(value: str, language: str) -> str | None:
    match = _LEGAL_FR_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    return (
        f"décret numéro {_cardinal(int(match.group(1)), language)} "
        f"{_cardinal(int(match.group(2)), language)}"
    )


def _render_prefixed_paragraph(value: str, language: str) -> str | None:
    match = _LEGAL_PREFIX_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    result = f"{_digitwise(match.group(1), language)} Paragraf {_cardinal(int(match.group(2)), language)}"
    if match.group(3):
        result += f" Absatz {_cardinal(int(match.group(3)), language)}"
    return result


def _render_generic_legal(value: str, language: str) -> str | None:
    match = _LEGAL_GENERIC_VALUE_RE.fullmatch(value)
    if match is None:
        return None
    pair = _LEGAL_GENERIC_HEADINGS.get(base_language(language), _LEGAL_GENERIC_HEADINGS["en"])
    heading = pair[0] if value.lstrip().startswith("§") else pair[1]
    result = [heading, _cardinal(int(match.group(1)), language)]
    for group in match.groups()[1:3]:
        if group:
            result.append(
                _cardinal(int(group), language)
                if group.isdigit()
                else render_sequence(group, language=language)
            )
    result.append(render_sequence(match.group(4), language=language))
    return " ".join(result)


_LEGAL_RENDERERS = (
    _render_labeled_legal,
    _render_german_paragraph,
    _render_german_article,
    _render_german_roman,
    _render_us_code,
    _render_spanish_law,
    _render_italian_law,
    _render_spanish_slash_reference,
    _render_italian_slash_reference,
    _render_english_docket,
    _render_french_decree,
    _render_prefixed_paragraph,
    _render_generic_legal,
)


def _legal_text(value: str, language: str) -> str:
    for renderer in _LEGAL_RENDERERS:
        rendered = renderer(value, language)
        if rendered is not None:
            return rendered
    return render_sequence(value, language=language)


def _address_text(number: str, suffix: str, street: str, language: str) -> str:
    return (
        f"{render_sequence(number, language=language)} {_grapheme_text(suffix, language)} {street}"
    )


def _street_address_text(match: re.Match[str], language: str) -> str:
    value = _cardinal(int(match["number"]), language)
    if match["suffix"]:
        value += f" {_grapheme_text(match['suffix'], language)}"
    if match["range"]:
        value += f" bis {_cardinal(int(match['range']), language)}"
    if match["slash"]:
        separator = {"de": "Schrägstrich", "fr": "barre", "es": "barra", "it": "barra"}.get(
            base_language(language), "slash"
        )
        value += f" {separator} {_cardinal(int(match['slash']), language)}"
    return f"{match['street']} {value}"


def _reverse_address_text(match: re.Match[str], language: str) -> str:
    number = (
        _digitwise(match["number"], language)
        if base_language(language) in {"en", "fr"}
        else _cardinal(int(re.sub(r"[A-Za-z]", "", match["number"])), language)
    )
    if match["suffix"]:
        number += f" {_grapheme_text(match['suffix'], language)}"
    labels = {
        "st": "Street",
        "street": "Street",
        "rd": "Road",
        "road": "Road",
        "ave": "Avenue",
        "avenue": "Avenue",
        "blvd": "Boulevard",
        "boulevard": "Boulevard",
    }
    kind = labels.get(match["kind"].casefold().rstrip("."), match["kind"])
    return f"{number} {match['street']} {kind}"


def _leading_address_text(match: re.Match[str], language: str) -> str:
    number = _digitwise(match["number"], language)
    return f"{number} {_grapheme_text(match['suffix'], language)} {match['street']}"


def _add(
    candidates: list[Replacement],
    match: re.Match[str],
    value: str,
    language: str,
    rule: str,
    protected: tuple[tuple[int, int], ...],
    evidence_source: str | None = None,
    evidence_score: float | None = None,
    evidence_cues: tuple[str, ...] = (),
) -> None:
    if _claimed(match.start(), match.end(), protected):
        specificity = {
            "sequence.biology": 20,
            "sequence.countdown": 90,
            "sequence.chained-score": 88,
            "sequence.duration": 95,
            "sequence.formula": 20,
            "sequence.coordinate": 86,
            "sequence.isbn": 30,
            "sequence.product": 15,
            "sequence.plate": 15,
            "sequence.math": 5,
        }.get(rule, 0)
        candidates.append(
            Replacement(
                match.start(),
                match.end(),
                value,
                "structured",
                language,
                rule,
                specificity,
                None,
                None,
                evidence_source,
                evidence_score,
                evidence_cues,
            )
        )


def _iter_quarter_height_postal_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
    *,
    promote_literals: bool = False,
    evidence: EvidenceSession | None = None,
) -> None:
    for match in _QUARTER_RE.finditer(text):
        start, end = match.span()
        if not _claimed(start, end, protected):
            continue
        before = text[max(0, start - 24) : start]
        if re.search(r"\b(?:model|part)\s*$", before, re.IGNORECASE):
            continue
        quarter = int(match["quarter"])
        year = int(match["year"]) if match["year"] else None
        fiscal_year = int(match["fy_year"]) if match["fy_year"] else None
        candidates.append(
            Replacement(
                start,
                end,
                _quarter_text(quarter, language, year, fiscal_year),
                "structured",
                language,
                "sequence.quarter",
                78,
            )
        )

    if base_language(language) == "de":
        for match in _HEIGHT_RE.finditer(text):
            if _claimed(match.start(), match.end(), protected):
                meters = int(match["meters"])
                centimeters = int(match["centimeters"])
                meter_word = "Meter" if meters == 1 else "Meter"
                candidates.append(
                    Replacement(
                        match.start(),
                        match.end(),
                        f"{'ein' if meters == 1 else _cardinal(meters, language)} {meter_word} {_cardinal(centimeters, language)}",
                        "structured",
                        language,
                        "sequence.height",
                        72,
                    )
                )

    if base_language(language) == "es":
        for match in _ES_POSTAL_RE.finditer(text):
            _add(
                candidates,
                match,
                f"{match['label']} {_digitwise(match['value'], language)}",
                language,
                "sequence.postal",
                protected,
            )

    for pattern, rule in ((_URL_RE, "sequence.url"), (_EMAIL_RE, "sequence.email")):
        for match in pattern.finditer(text):
            _add(
                candidates,
                match,
                (
                    _url_text(match.group(0), language, evidence=evidence)
                    if rule == "sequence.url"
                    else _email_text(match.group(0), language)
                ),
                language,
                rule,
                protected,
            )

    if promote_literals:
        for match in _BARE_DOMAIN_RE.finditer(text):
            _add(
                candidates,
                match,
                _url_text(match.group(0), language, evidence=evidence),
                language,
                "sequence.url",
                protected,
            )


def _iter_finance_quantity_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _EXCHANGE_EQUAL_RE.finditer(text):
        left_code = _CURRENCY_SYMBOL_CODES.get(
            match["left_currency"], match["left_currency"].upper()
        )
        right_raw = match["right_currency"] or ""
        right_code = _CURRENCY_SYMBOL_CODES.get(right_raw, right_raw.upper())
        _add(
            candidates,
            match,
            f"{_currency_code_text(match['left_number'], left_code, language)} equals "
            f"{_currency_code_text(match['right_number'], right_code, language)}",
            language,
            "sequence.exchange-rate",
            protected,
        )

    for match in _EXCHANGE_TO_RE.finditer(text):
        source_code = _CURRENCY_SYMBOL_CODES.get(match["currency"], match["currency"].upper())
        target_code = _CURRENCY_SYMBOL_CODES.get(match["target"], match["target"].upper())
        _add(
            candidates,
            match,
            f"{_currency_code_text(match['number'], source_code, language)} to "
            f"{_CURRENCY_CODE_NAMES.get(target_code, {}).get(base_language(language), target_code)}",
            language,
            "sequence.exchange-rate",
            protected,
        )

    for match in _EXCHANGE_SLASH_RE.finditer(text):
        source_code = match["currency"].upper()
        target_code = match["target"].upper()
        _add(
            candidates,
            match,
            f"{_currency_code_text(match['number'], source_code, language)} per "
            f"{_CURRENCY_CODE_NAMES.get(target_code, {}).get(base_language(language), target_code)}",
            language,
            "sequence.exchange-rate",
            protected,
        )

    for match in _CURRENCY_MAGNITUDE_RE.finditer(text):
        symbol = match["symbol"]
        value = f"{_decimal_text(match['number'], language)} {match['magnitude']}"
        currency_names = {"€": "euro", "$": "dollars", "£": "pounds"}
        _add(
            candidates,
            match,
            f"{value} {currency_names[symbol]}",
            language,
            "sequence.currency-magnitude",
            protected,
        )

    for match in _CURRENCY_SYMBOL_RE.finditer(text):
        symbol = match["prefix"] or match["suffix"]
        if symbol and base_language(language) in {"de", "it"}:
            _add(
                candidates,
                match,
                _currency_symbol_text(match["number"], symbol, language),
                language,
                "sequence.currency",
                protected,
            )

    for match in _PERCENT_RE.finditer(text):
        _add(
            candidates,
            match,
            _percent_text(match["value"], language),
            language,
            "sequence.percent",
            protected,
        )

    for match in _COMPOUND_UNIT_RE.finditer(text):
        _add(
            candidates,
            match,
            _compound_unit_text(match["number"], match["unit"], language),
            language,
            "sequence.compound-unit",
            protected,
        )

    for match in _FRACTION_RE.finditer(text):
        _add(
            candidates,
            match,
            _fraction_text(match["whole"], match["fraction"], language),
            language,
            "sequence.fraction",
            protected,
        )

    for match in _SLASH_FRACTION_RE.finditer(text):
        numerator = match["numerator"] or match["numerator_only"]
        denominator = match["denominator"] or match["denominator_only"]
        if numerator is None or denominator is None:
            continue
        slash_value = _slash_fraction_text(match["whole"], numerator, denominator, language)
        if slash_value is not None:
            _add(candidates, match, slash_value, language, "sequence.fraction", protected)

    for match in _COORDINATE_RE.finditer(text):
        direction = match["direction"]
        if base_language(language) == "it" and direction is None:
            # In Italian an attached degree marker is an ordinal unless a
            # directional coordinate makes the semantic reading unambiguous.
            continue
        if _coordinate_is_valid(match["value"], direction):
            _add(
                candidates,
                match,
                _coordinate_text(match["value"], direction, language),
                language,
                "sequence.coordinate",
                protected,
            )


def _iter_identifier_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _ISBN_RE.finditer(text):
        if _isbn_shape_is_valid(match["value"]):
            label = _isbn_label_text(match["label"], language)
            _add(
                candidates,
                match,
                f"{label} {_isbn_text(match['value'], language)}",
                language,
                "sequence.isbn",
                protected,
            )

    for label_match in _ISBN_LABEL_RE.finditer(text):
        search_start = label_match.end()
        search_end = min(len(text), search_start + 96)
        tail = text[search_start:search_end]
        for value_match in _ISBN_VALUE_RE.finditer(tail):
            value = value_match["value"]
            if not _isbn_shape_is_valid(value):
                continue
            value_start = search_start + value_match.start("value")
            value_end = search_start + value_match.end("value")
            if not _claimed(value_start, value_end, protected):
                continue
            candidates.append(
                Replacement(
                    label_match.start(),
                    label_match.end(),
                    _isbn_label_text(label_match["label"], language),
                    "structured",
                    language,
                    "sequence.isbn",
                    35,
                )
            )
            candidates.append(
                Replacement(
                    value_start,
                    value_end,
                    _isbn_text(value, language),
                    "structured",
                    language,
                    "sequence.isbn",
                    35,
                )
            )
            break

    for label_match in _SPACED_ISBN_LABEL_RE.finditer(text):
        search_start = label_match.end()
        tail = text[search_start : min(len(text), search_start + 96)]
        spaced_value_match = _ISBN_VALUE_RE.search(tail)
        if spaced_value_match is None or not _isbn_is_valid(spaced_value_match["value"]):
            continue
        value_start = search_start + spaced_value_match.start("value")
        value_end = search_start + spaced_value_match.end("value")
        if not _claimed(value_start, value_end, protected):
            continue
        candidates.extend(
            (
                Replacement(
                    label_match.start(),
                    label_match.end(),
                    _grapheme_text("ISBN", language),
                    "structured",
                    language,
                    "sequence.isbn",
                    36,
                ),
                Replacement(
                    value_start,
                    value_end,
                    _isbn_text(spaced_value_match["value"], language),
                    "structured",
                    language,
                    "sequence.isbn",
                    36,
                ),
            )
        )

    for match in _UUID_RE.finditer(text):
        _add(
            candidates,
            match,
            _punctuated(match["value"], language),
            language,
            "sequence.uuid",
            protected,
        )

    for match in _IPV4_RE.finditer(text):
        octets = match["value"].split(".")
        if all(int(octet) <= 255 for octet in octets):
            _add(
                candidates,
                match,
                _ip_text(match["value"], language),
                language,
                "sequence.ipv4",
                protected,
            )

    for match in _MAC_RE.finditer(text):
        _add(
            candidates,
            match,
            _mac_text(match["value"], language),
            language,
            "sequence.mac",
            protected,
        )

    for match in _IBAN_RE.finditer(text):
        _add(
            candidates,
            match,
            _punctuated(match["value"].replace(" ", ""), language),
            language,
            "sequence.iban",
            protected,
        )

    for match in _PHONE_RE.finditer(text):
        prefix = text[max(0, match.start() - 48) : match.start()]
        blocked = bool(_PHONE_BLOCKING_CONTEXT_RE.search(prefix))
        has_context = _phone_context(text, match.start(), match.end(), match["value"])
        if (
            not blocked
            and not _looks_like_date_shape(match["value"])
            and (
                _phone_is_plausible(match["value"])
                or (
                    has_context
                    and len(re.sub(r"\D", "", match["value"])) >= 7
                    and not re.search(r"[.,]", match["value"])
                    and (
                        re.search(
                            r"\b(?:centralino|numero\s+(?:di\s+)?(?:telefono|aziendale|di\s+casa)|telefonnummer)\b",
                            prefix,
                            re.IGNORECASE,
                        )
                        or re.search(r"[ ()/\-]", match["value"])
                    )
                )
            )
        ):
            if has_context and _claimed(match.start(), match.end(), protected):
                candidates.append(
                    Replacement(
                        match.start(),
                        match.end(),
                        _phone_text(match["value"], language),
                        "structured",
                        language,
                        "sequence.phone",
                        78,
                    )
                )
            elif len(re.sub(r"\D", "", match["value"])) == 7 and _claimed(
                match.start(), match.end(), protected
            ):
                candidates.append(
                    Replacement(
                        match.start(),
                        match.end(),
                        match["value"],
                        "structured",
                        language,
                        "sequence.phone-ambiguous",
                        74,
                    )
                )

    for match in _ITALIAN_SERIAL_RE.finditer(text):
        start, end = match.span("value")
        if _claimed(start, end, protected):
            replacement = ", ".join(
                _digitwise(group, language) for group in match["value"].split("-")
            )
            candidates.append(
                Replacement(start, end, replacement, "structured", language, "sequence.product", 79)
            )

    for match in _EMERGENCY_RE.finditer(text):
        policy = _EMERGENCY_POLICIES.get(base_language(language), EmergencyNumberPolicy())
        number = (
            _digitwise(match["value"], language)
            if policy.mode == "digitwise"
            else _cardinal(int(match["value"]), language)
        )
        _add(
            candidates,
            match,
            match.group(0).replace(match["value"], number),
            language,
            "sequence.emergency",
            protected,
        )


def _iter_version_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
    *,
    promote_literals: bool = False,
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    evidence: EvidenceSession | None = None,
) -> None:
    for match in _VERSION_CONTEXT_RE.finditer(text):
        value = match["value"]
        start, end = match.start("value"), match.end("value")
        if _claimed(start, end, protected) and (
            promote_literals or not value.casefold().startswith("v")
        ):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _version_text(value, language),
                    "structured",
                    language,
                    "sequence.version",
                )
            )

    for match in _SOFTWARE_VERSION_RE.finditer(text):
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _version_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.version",
                    2,
                )
            )

    for match in _VERSION_RE.finditer(text):
        prefix = text[max(0, match.start() - 32) : match.start()]
        contextual = bool(
            re.search(r"\b(?:version|release|ver\.?|build)\s*[=:]?\s*$", prefix, re.IGNORECASE)
        )
        if promote_literals or (not contextual and not match["value"].casefold().startswith("v")):
            _add(
                candidates,
                match,
                _version_text(
                    match["value"],
                    language,
                    include_version_word=promote_literals and base_language(language) == "en",
                ),
                language,
                "sequence.version",
                protected,
            )

    if (
        interpretation_mode is InterpretationMode.CONTEXTUAL
        and evidence is not None
        and evidence.available
    ):
        for match in _GENERIC_DOTTED_VERSION_RE.finditer(text):
            start, end = match.span("value")
            value = match["value"]
            octets = value.split(".")
            if len(octets) == 4 and all(int(octet) <= 255 for octet in octets):
                continue
            if not _claimed(start, end, protected):
                continue
            domain_evidence = evidence.supports(text, target=(start, end), domain="computing")
            if domain_evidence is None:
                continue
            details = EvidenceSession.details("computing", domain_evidence)
            candidates.append(
                Replacement(
                    start,
                    end,
                    _version_text(value, language),
                    "structured",
                    language,
                    "sequence.version",
                    76,
                    evidence_source=details.source if details else None,
                    evidence_score=details.score if details else None,
                    evidence_cues=details.cues if details else (),
                )
            )


def _iter_roman_symbol_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    roman_patterns: tuple[tuple[re.Pattern[str], RomanSemantic], ...] = (
        (_ROMAN_PREFIX_CARDINAL_RE, "cardinal"),
        (_ROMAN_PREFIX_ORDINAL_RE, "ordinal"),
        (_ROMAN_SUFFIX_ORDINAL_RE, "ordinal"),
        (_ROMAN_YEAR_CONTEXT_RE, "year"),
        (_ROMAN_CLOCK_RE, "cardinal"),
        (_ROMAN_NUMBERED_PREFIX_RE, "cardinal"),
        (_ROMAN_NUMBERED_SUFFIX_RE, "cardinal"),
    )

    for pattern, semantic in roman_patterns:
        for match in pattern.finditer(text):
            if not _roman_is_valid(match["value"]):
                continue
            start, end = match.span("value")
            if match.groupdict().get("suffix") is not None:
                end = match.end("suffix")
            if _claimed(start, end, protected):
                candidates.append(
                    Replacement(
                        start,
                        end,
                        _roman_text(
                            match["value"],
                            semantic=semantic,
                            language=language,
                            context=match.groupdict().get("context"),
                        ),
                        "structured",
                        language,
                        "sequence.roman",
                    )
                )

    for match in _SUPERSCRIPT_RE.finditer(text):
        if _claimed(match.start(), match.end(), protected):
            _add(
                candidates,
                match,
                _math_text(match.group(0), language),
                language,
                "sequence.math",
                protected,
            )

    for match in _GREEK_TOKEN_RE.finditer(text):
        if _claimed(match.start(), match.end(), protected):
            _add(
                candidates,
                match,
                _GREEK_NAMES[match["value"]],
                language,
                "sequence.symbol",
                protected,
            )

    monarch_pattern = {
        "de": _DE_MONARCH_RE,
        "fr": _FR_MONARCH_RE,
        "it": _IT_MONARCH_RE,
        "pt": _PT_MONARCH_RE,
    }.get(base_language(language), _EN_MONARCH_RE)

    for match in monarch_pattern.finditer(text):
        if not _roman_is_valid(match["value"]):
            continue
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _roman_text(
                        match["value"],
                        semantic="monarch",
                        language=language,
                        context=match["context"],
                    ),
                    "structured",
                    language,
                    "sequence.roman",
                )
            )

    for pattern, marker, rule in (
        (_HASHTAG_RE, "#", "sequence.social-hashtag"),
        (_MENTION_RE, "@", "sequence.social-mention"),
    ):
        for match in pattern.finditer(text):
            prefix = text[max(0, match.start() - 32) : match.start()]
            marker_already_named = bool(
                re.search(
                    r"(?:hashtag|almohadilla|dièse|hashtag|arroba|arobase|chiocciola|at)\s*$",
                    prefix,
                    re.IGNORECASE,
                )
            )
            _add(
                candidates,
                match,
                _marker_text(
                    marker,
                    match["value"],
                    language,
                    include_marker=not marker_already_named,
                ),
                language,
                rule,
                protected,
            )


def _iter_math_science_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for pattern in (_MATH_ABSOLUTE_RE, _MATH_RE):
        for match in pattern.finditer(text):
            if not _math_is_plausible(match["value"], text, match.start()):
                continue
            _add(
                candidates,
                match,
                _math_text(match["value"], language),
                language,
                "sequence.math",
                protected,
            )

    for match in _MUSIC_CONTEXT_RE.finditer(text):
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _music_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.music",
                )
            )

    for match in _TEMPO_RE.finditer(text):
        tempo_words = {
            "de": "Viertelnote gleich",
            "en": "quarter note equals",
            "es": "negra igual a",
            "fr": "noire égale",
            "it": "semiminima uguale",
        }
        value = f"{tempo_words.get(base_language(language), tempo_words['en'])} {_cardinal(int(match['value']), language)}"
        _add(candidates, match, value, language, "sequence.music", protected)

    for match in _BIOLOGY_RE.finditer(text):
        if not _biology_is_plausible(match["value"], text, match.start()):
            continue
        _add(
            candidates,
            match,
            _biology_text(match["value"], language),
            language,
            "sequence.biology",
            protected,
        )

    for match in _FORMULA_RE.finditer(text):
        if _formula_is_plausible(match["value"]) and _formula_context_is_balanced(
            text, match.start("value"), match.end("value")
        ):
            _add(
                candidates,
                match,
                _formula_text(match["value"], language),
                language,
                "sequence.formula",
                protected,
            )


def _iter_initialism_ticker_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _PAREN_INITIALISM_RE.finditer(text):
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _grapheme_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.parenthesized-initialism",
                    79,
                )
            )

    for match in _PAREN_TICKER_RE.finditer(text):
        prefix = text[max(0, match.start() - 48) : match.start()]
        suffix = text[match.end() : match.end() + 48]
        if not re.search(
            r"\b(?:stock|share|ticker|symbol|aktie|acción|azione|action)\b",
            f"{prefix} {suffix}",
            re.IGNORECASE,
        ):
            continue
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _grapheme_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.parenthesized-ticker",
                    80,
                )
            )

    for match in _TICKER_RE.finditer(text):
        value = f"dollar {_ticker_text(match['value'], language)}"
        _add(candidates, match, value, language, "sequence.ticker", protected)

    for match in _TICKER_CONTEXT_RE.finditer(text):
        ticker = match["value"]
        if ticker != ticker.upper():
            continue
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _ticker_text(ticker, language),
                    "structured",
                    language,
                    "sequence.ticker",
                    80,
                )
            )

    for match in _EXCHANGE_TICKER_RE.finditer(text):
        ticker = match["value"]
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _ticker_text(ticker, language),
                    "structured",
                    language,
                    "sequence.ticker",
                    80,
                )
            )


def _iter_product_vehicle_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _PRODUCT_RE.finditer(text):
        raw_value = match["value"]
        if not _valid_product_candidate(match["label"], raw_value):
            continue
        if len(raw_value.rstrip(".")) == 1 and raw_value.rstrip(".").isalpha():
            continue
        raw_label = match["label"].strip()
        label_key = raw_label.casefold().replace(".", "")
        label = product_label_text(label_key, raw_label)
        category = product_label_category(label_key)
        value = _typed_code_text(match["value"], language, category=category)
        label = (
            _grapheme_text(label, language)
            if label in {"SKU", "VIN", "IMEI", "ICCID", "PIN", "RFC"}
            else label
        )
        _add(candidates, match, f"{label} {value}", language, "sequence.product", protected)

    for match in _PLATE_CONTEXT_RE.finditer(text):
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="license"),
            language,
            "sequence.plate",
            protected,
        )

    for match in _VIN_RE.finditer(text):
        if any(character.isalpha() for character in match["value"]) and any(
            character.isdigit() for character in match["value"]
        ):
            _add(
                candidates,
                match,
                _typed_code_text(match["value"], language, category="vin"),
                language,
                "sequence.vin",
                protected,
            )

    for match in _VEHICLE_MODEL_RE.finditer(text):
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _typed_code_text(match["value"], language, category="model"),
                    "structured",
                    language,
                    "sequence.product",
                    20,
                )
            )

    for match in _CODE_RE.finditer(text):
        code_category = "vehicle" if re.search(r"\d+[A-Z]+\d", match["value"]) else "product"
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category=code_category),
            language,
            "sequence.product",
            protected,
        )

    for match in _PLATE_RE.finditer(text):
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="license"),
            language,
            "sequence.plate",
            protected,
        )

    for match in _COMPACT_PLATE_RE.finditer(text):
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="license"),
            language,
            "sequence.plate",
            protected,
        )

    for match in _SPACED_PLATE_RE.finditer(text):
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="license"),
            language,
            "sequence.plate",
            protected,
        )

    for match in _COMPACT_VEHICLE_RE.finditer(text):
        vehicle_prefix = re.match(r"[A-Z]+", match["value"], re.IGNORECASE)
        if (
            vehicle_prefix is None
            or vehicle_prefix.group(0).upper() not in _REVIEWED_VEHICLE_PREFIXES
        ):
            continue
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="vehicle"),
            language,
            "sequence.product",
            protected,
        )

    for match in _MIXED_ACRONYM_RE.finditer(text):
        _add(
            candidates,
            match,
            _grapheme_text(match["value"], language),
            language,
            "sequence.acronym",
            protected,
        )

    for pattern in (
        _LEGAL_RE,
        _LEGAL_PREFIX_RE,
        _LEGAL_US_RE,
        _LEGAL_ES_RE,
        _LEGAL_IT_RE,
        _LEGAL_FR_RE,
        _LEGAL_ES_SLASH_RE,
        _LEGAL_IT_SLASH_RE,
        _LEGAL_DOCKET_RE,
        _LEGAL_LABEL_RE,
    ):
        for match in pattern.finditer(text):
            _add(
                candidates,
                match,
                _legal_text(match["value"], language),
                language,
                "sequence.legal",
                protected,
            )


def _iter_duration_sports_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
    evidence: EvidenceSession | None = None,
) -> None:
    for match in _DURATION_RE.finditer(text):
        _add(
            candidates,
            match,
            _duration_text(match["hour"], match["minute"], match["second"], language),
            language,
            "sequence.duration",
            protected,
        )

    for match in _CHAINED_SCORE_RE.finditer(text):
        if countdown_is_plausible(text, match.start(), language):
            _add(
                candidates,
                match,
                countdown_text(match["value"], language),
                language,
                "sequence.countdown",
                protected,
            )
        elif _chained_score_is_plausible(text, match.start(), match.end(), evidence=evidence):
            values = re.split(r"\s*[-–]\s*", match["value"])
            connector = {"de": "zu", "es": "a", "fr": "à", "it": "a"}.get(
                base_language(language), "to"
            )
            sports_evidence = (
                evidence.supports(text, target=(match.start(), match.end()), domain="sports")
                if evidence is not None and evidence.available
                else None
            )
            sports_details = EvidenceSession.details("sports", sports_evidence)
            _add(
                candidates,
                match,
                f" {connector} ".join(_cardinal(int(value), language) for value in values),
                language,
                "sequence.chained-score",
                protected,
                evidence_source=sports_details.source if sports_details else None,
                evidence_score=sports_details.score if sports_details else None,
                evidence_cues=sports_details.cues if sports_details else (),
            )

    for match in _SCORE_RE.finditer(text):
        if _score_is_plausible(
            match["value"], text, match.start(), match.end(), evidence=evidence
        ) and _claimed(match.start(), match.end(), protected):
            sports_evidence = (
                evidence.supports(text, target=(match.start(), match.end()), domain="sports")
                if evidence is not None and evidence.available
                else None
            )
            sports_details = EvidenceSession.details("sports", sports_evidence)
            candidates.append(
                Replacement(
                    match.start(),
                    match.end(),
                    _score_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.sports",
                    84,
                    evidence_source=sports_details.source if sports_details else None,
                    evidence_score=sports_details.score if sports_details else None,
                    evidence_cues=sports_details.cues if sports_details else (),
                )
            )

    for match in _SPORTS_RE.finditer(text):
        start, end = match.start("value"), match.end("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _score_text(match["value"], language),
                    "structured",
                    language,
                    "sequence.sports",
                )
            )


def _iter_address_candidates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _DOTTED_LEXICAL_RE.finditer(text):
        _add(candidates, match, "uncle", language, "sequence.acronym", protected)

    for match in _ADDRESS_SUFFIX_RE.finditer(text):
        _add(
            candidates,
            match,
            _address_text(match["number"], match["suffix"], match["street"], language),
            language,
            "sequence.address",
            protected,
        )

    for match in _ADDRESS_RE.finditer(text):
        _add(
            candidates,
            match,
            _street_address_text(match, language),
            language,
            "sequence.address",
            protected,
        )

    for match in _ADDRESS_CONTEXT_RE.finditer(text):
        _add(
            candidates,
            match,
            _street_address_text(match, language),
            language,
            "sequence.address",
            protected,
        )

    for match in _ADDRESS_REVERSE.finditer(text):
        _add(
            candidates,
            match,
            _reverse_address_text(match, language),
            language,
            "sequence.address",
            protected,
        )

    for match in _LEADING_ADDRESS_RE.finditer(text):
        _add(
            candidates,
            match,
            _leading_address_text(match, language),
            language,
            "sequence.address",
            protected,
        )

    for match in _ADDRESS_COMPONENT_RE.finditer(text):
        label = match["label"].casefold().rstrip(".")
        label_words = {
            "apt": "Apartment",
            "apartment": "Apartment",
            "suite": "Suite",
            "piso": "piso",
            "departamento": "departamento",
            "interior": "interior",
            "local": "local",
            "unité": "unité",
            "appartement": "appartement",
            "tor": "Tor",
            "einheit": "Einheit",
        }
        number = (
            _digitwise(match["number"], language)
            if base_language(language) in {"fr"}
            else _cardinal(int(re.sub(r"[A-Za-z]", "", match["number"])), language)
        )
        _add(
            candidates,
            match,
            f"{label_words.get(label, match['label'])} {number}",
            language,
            "sequence.address",
            protected,
        )

    for match in _POSTBOX_RE.finditer(text):
        _add(
            candidates,
            match,
            f"{match['label']} {_digitwise(match['number'], language)}",
            language,
            "sequence.address",
            protected,
        )

    for match in _FLOOR_RE.finditer(text):
        label = (
            "Obergeschoss"
            if base_language(language) == "de" and match["label"].casefold() == "og"
            else match["label"]
        )
        if base_language(language) == "de" and match["label"].casefold() == "og":
            number = str(
                number_words(
                    int(match["number"]),
                    lang=language,
                    to="ordinal",
                )
            )
            if number.endswith("e"):
                number += "s"
            value = f"{number} {label}"
        else:
            value = f"{_cardinal(int(match['number']), language)} {label}"
        _add(candidates, match, value, language, "sequence.address", protected)

    if base_language(language) == "de":
        for match in _POSTAL_CITY_RE.finditer(text):
            prefix = text[max(0, match.start() - 24) : match.start()]
            has_postal_cue = bool(
                re.search(r"(?:PLZ|Postleitzahl|postal|postcode)\s*$", prefix, re.IGNORECASE)
            )
            if has_postal_cue or match["city"] in _POSTAL_CITY_NAMES:
                _add(
                    candidates,
                    match,
                    f"{_digitwise(match['postal'], language)} {match['city']}",
                    language,
                    "sequence.address",
                    protected,
                )


def iter_sequence_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: Literal[
        "known_only", "conservative_unknown", "spell_unknown"
    ] = "known_only",
    generic_acronym_case: Literal["upper", "lower"] = "upper",
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    evidence: EvidenceSession | None = None,
    trace: TraceCollector | None = None,
) -> tuple[Replacement, ...]:
    """Recognize and render high-confidence atomic structured sequences."""
    language = normalize_language(language)
    if base_language(language) == "sv":
        return ()
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    candidates.extend(
        iter_biomedical_replacements(text, language=language, protected_ranges=protected)
    )
    candidates.extend(
        iter_range_replacements(text, language=language, protected_ranges=protected, trace=trace)
    )
    candidates.extend(
        iter_reference_replacements(text, language=language, protected_ranges=protected)
    )
    _iter_quarter_height_postal_candidates(
        text, language, protected, candidates, promote_literals=promote_literals, evidence=evidence
    )
    _iter_finance_quantity_candidates(text, language, protected, candidates)
    _iter_identifier_candidates(text, language, protected, candidates)
    _iter_version_candidates(
        text,
        language,
        protected,
        candidates,
        promote_literals=promote_literals,
        interpretation_mode=interpretation_mode,
        evidence=evidence,
    )
    _iter_roman_symbol_candidates(text, language, protected, candidates)
    _iter_math_science_candidates(text, language, protected, candidates)
    _iter_initialism_ticker_candidates(text, language, protected, candidates)
    _iter_product_vehicle_candidates(text, language, protected, candidates)
    _iter_duration_sports_candidates(text, language, protected, candidates, evidence=evidence)
    _iter_address_candidates(text, language, protected, candidates)
    return tuple(candidates)


__all__ = ["iter_sequence_replacements"]
