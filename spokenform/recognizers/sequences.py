"""High-confidence atomic recognizers for structured character sequences."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from num2words import num2words

from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme
from ..sequences import SequenceRenderPolicy, render_letters, render_sequence, vocabulary

_FRACTION_CHARS = "½⅓⅔¼¾⅛⅜⅝⅞"
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
_ISBN_VALUE_RE = re.compile(r"(?<!\w)(?P<value>(?:97[89][ -]?)?\d(?:[\d -]*\d|X|x))(?!\w)")
_CODE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,8}-\d{2,8}(?:-[A-Z0-9]{1,8})*)(?!\w)")
_PLATE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,3}\d{1,4}[A-Z]{1,3})(?!\w)")
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
    r"(?:isbn(?:-1[03])?|legal|section|article|version|release|serial(?:\s+number)?|sku|model|product(?:\s+code)?|imei|iccid|mac|ip|vin|pin|uuid|\u00a7|art\.)\s*[:#-]?\s*(?:is\s+|for\s+[^\n]{0,32}\s+is\s+)?$",
    re.IGNORECASE,
)
_EMERGENCY_RE = re.compile(
    r"\b(?:call|dial|emergency|notruf|emergencia|número\s+de\s+emergencia|urgence|numéro\s+d['’]urgence|emergenza|numero\s+di\s+emergenza)\s*[:#-]?\s*(?P<value>110|112|911|999)\b",
    re.IGNORECASE,
)
_VERSION_CONTEXT_RE = re.compile(
    r"(?P<label>\b(?:version|release|ver\.?|build)\s*[=:]?\s*)(?P<value>v?\d+(?:\.\d+){2,}(?:[a-z]+\d*)?)",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"(?<!\w)(?P<value>v\d+(?:\.\d+){1,}(?:-[A-Za-z0-9]+)?)(?!\w)",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"(?<!\w)(?:https?://|www\.)[^\s<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
_ROMAN_CONTEXT_RE = re.compile(
    r"(?P<context>\b(?:chapter|volume|part|section|century|king|queen|pope|super\s+bowl|kapitel|band|teil|abschnitt|siglo|capítulo|chapitre|capitolo)\s+)"
    r"(?P<value>[IVXLCDM]{1,12})(?![A-Za-z])",
    re.IGNORECASE,
)
_ROMAN_YEAR_RE = re.compile(
    r"(?P<context>\b(?:im\s+jahr|anno|year)\s+)(?P<value>[IVXLCDM]{2,12})(?![A-Za-z])",
    re.IGNORECASE,
)
_MONARCH_RE = re.compile(
    r"(?P<name>Heinrich|Wilhelm|Ludwig|Karl|Friedrich|Elizabeth|Charles|Henry)\s+(?P<value>[IVXLCDM]{1,12})\.(?![A-Za-z])",
    re.IGNORECASE,
)
_HASHTAG_RE = re.compile(r"(?<!\w)#(?P<value>[\wÀ-ž](?:[\wÀ-ž_-]*[\wÀ-ž])?)", re.UNICODE)
_MENTION_RE = re.compile(r"(?<!\w)@(?P<value>[\wÀ-ž](?:[\wÀ-ž_-]*[\wÀ-ž])?)", re.UNICODE)
_FORMULA_RE = re.compile(
    r"(?<!\w)(?P<value>(?:(?:[A-Z][a-z]?)+|\((?:[A-Z][a-z]?)+\)[0-9₀-₉]+|[A-Z][a-z]?[0-9₀-₉]+)+)(?!\w)"
)
_MATH_RE = re.compile(
    r"(?<!\w)(?P<value>(?:√\s*)?(?:[A-Za-z]|\d+(?:[.,]\d+)?|\([^()]+\)|[⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*(?:[+−*=×÷<>^\-])\s*"
    r"(?:√\s*)?(?:[A-Za-z]|\d+(?:[.,]\d+)?|\([^()]+\)|[⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?:\s*(?:[+−*=×÷<>^\-])\s*(?:[A-Za-z]|\d+(?:[.,]\d+)?|\([^()]+\)|[⁰¹²³⁴⁵⁶⁷⁸⁹]+))*)(?!\w)"
)
_MUSIC_CONTEXT_RE = re.compile(
    r"\b(?:chord|note|key|tonality|akkord|stück|stück|tonart|nota|accord|accordo)\b[^\n,]{0,24}?"
    r"(?P<value>[A-Ga-g](?:[#b♯♭])?(?:[-]?(?:Dur|Moll)|m|maj|min|dim|sus)?\d*)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_TEMPO_RE = re.compile(r"(?P<note>[♩♪♫])\s*=\s*(?P<value>\d{1,3})(?!\w)")
_BIOLOGY_RE = re.compile(
    r"(?<!\w)(?P<value>[A-Z]\.\s*[a-z][a-z-]{2,}(?:\s+(?:strain|subsp\.)\s*[A-Za-z0-9-]+)?)(?!\w)"
)
_ACRONYM_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,8})(?!\w)")
_MIXED_ACRONYM_RE = re.compile(r"(?<!\w)(?P<value>[A-Z][a-z]{1,4}[A-Z])(?!\w)")
_TICKER_RE = re.compile(r"(?<!\w)\$(?P<value>[A-Z]{1,5})(?!\w)")
_PRODUCT_RE = re.compile(
    r"(?P<label>Serial\s+number|Part\s+number|Product\s+code|SN|S/N|Serial|SKU|Model|Modelo|VIN|IMEI|ICCID|PIN|Part|Product)\s*(?:[:#]\s*|\s+)(?:No\.\s*)?(?P<value>[A-Za-z0-9][A-Za-z0-9-]{1,})",
    re.IGNORECASE,
)
_LEGAL_RE = re.compile(
    r"(?<!\w)(?P<value>(?:§|Art\.?|Artikel)\s*\d+(?:\s+(?:Abs\.?\s*\d+|[IVXLCDM]+))?(?:\s+\d+)?\s+[A-ZÄÖÜ]{2,})(?!\w)",
)
_LEGAL_PREFIX_RE = re.compile(
    r"(?<!\w)(?P<value>(?:BGB|StGB|StVO|GG|VwGO|HGB|AO)\s+§\s*\d+(?:\s+Abs\.?\s*\d+)?)(?!\w)"
)
_LEGAL_US_RE = re.compile(r"(?<!\w)(?P<value>\d+\s+U\.S\.C\.\s+§\s*\d+)(?!\w)", re.IGNORECASE)
_LEGAL_ES_RE = re.compile(r"(?<!\w)(?P<value>ley\s+\d{1,3}(?:\.\d{3})?)(?!\w)", re.IGNORECASE)
_LEGAL_IT_RE = re.compile(r"(?<!\w)(?P<value>legge\s+n\.?\s*\d+(?:/\d{4})?)(?!\w)", re.IGNORECASE)
_LEGAL_FR_RE = re.compile(
    r"(?<!\w)(?P<value>(?:décret|decret)\s+n[°o]?\s*\d{4}-\d+)(?!\w)", re.IGNORECASE
)
_LEGAL_LABEL_RE = re.compile(
    r"(?<!\w)(?P<value>(?:section|sec\.?|article|art\.?|chapter|chap\.)\s*\d+(?:\s+(?:subsection|paragraph|para\.?|§)\s*\d+)?)(?!\w)",
    re.IGNORECASE,
)
_SPORTS_RE = re.compile(
    r"(?P<context>\b(?:score|final|match|game|football|basketball|handball|volleyball|set|satz|ergebnis|endergebnis|gewann|spiel|marcador|punteggio|partido|termin[oó]|victoria|ganaron|résultat|resultado|ganó|gagné|vinto)\b[^\d]{0,32})"
    r"(?P<value>\d{1,2}\s*(?::|[-–])\s*\d{1,2}|\d{1,2}\s+(?:a|to|à)\s+\d{1,2})",
    re.IGNORECASE,
)
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
}
_FRACTION_WORDS = {
    "en": {
        Fraction(1, 2): "one half",
        Fraction(1, 3): "one third",
        Fraction(2, 3): "two thirds",
        Fraction(1, 4): "one quarter",
        Fraction(3, 4): "three quarters",
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
        4: "quarter",
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
_ROMAN_ONLY = re.compile(r"^[IVXLCDM]+$")
_LEXICAL_UPPERCASE = frozenset({"API", "URL", "ISBN", "CHF", "EUR", "USD", "GBP", "HTTP", "HTTPS"})
_ELEMENT_SYMBOLS = frozenset(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)


@dataclass(frozen=True, slots=True)
class AcronymRenderPolicy:
    """Locale-specific pronunciation policy for uppercase tokens."""

    lexical_words: frozenset[str]
    initialisms: frozenset[str]
    preserve: frozenset[str]
    lexical_case: Literal["source-preserving", "sentence", "lower"] = "sentence"
    default_mode: Literal["lexical", "grapheme_spaced", "spoken_letter_names"] = (
        "spoken_letter_names"
    )


_COMMON_LEXICAL_ACRONYMS = frozenset({"NASA", "UNO", "FIFA", "UNESCO", "NATO"})
_COMMON_INITIALISMS = frozenset({"BND", "FBI", "CIA", "CD", "DVD"})
_ACRONYM_POLICIES: dict[str, AcronymRenderPolicy] = {
    "de": AcronymRenderPolicy(
        lexical_words=_COMMON_LEXICAL_ACRONYMS | {"RAF"},
        initialisms=_COMMON_INITIALISMS | {"ZDF", "DDR"},
        preserve=_LEXICAL_UPPERCASE,
    ),
    "en": AcronymRenderPolicy(
        lexical_words=frozenset({"NASA"}),
        initialisms=_COMMON_INITIALISMS | {"FBI", "CIA"},
        preserve=_LEXICAL_UPPERCASE,
    ),
    "es": AcronymRenderPolicy(
        lexical_words=_COMMON_LEXICAL_ACRONYMS | {"ONU"},
        initialisms=_COMMON_INITIALISMS | {"FBI", "CIA"},
        preserve=_LEXICAL_UPPERCASE,
    ),
    "fr": AcronymRenderPolicy(
        lexical_words=_COMMON_LEXICAL_ACRONYMS | {"ONU", "OTAN", "UNICEF"},
        initialisms=_COMMON_INITIALISMS
        | {"PDG", "OMS", "FBI", "SNCF", "CIO", "CNRS", "AFP", "RATP", "GPS"},
        preserve=_LEXICAL_UPPERCASE,
    ),
    "it": AcronymRenderPolicy(
        lexical_words=frozenset({"ONU", "UE", "CIA", "UNICEF", "IVA"}),
        initialisms=_COMMON_INITIALISMS
        | {"USA", "PIL", "FBI", "OMS", "CEO", "ATM", "GPS", "TV", "ADSL", "PC"},
        preserve=_LEXICAL_UPPERCASE,
    ),
}
for _base in ("pt", "cs"):
    _ACRONYM_POLICIES[_base] = AcronymRenderPolicy(
        lexical_words=_COMMON_LEXICAL_ACRONYMS,
        initialisms=_COMMON_INITIALISMS,
        preserve=_LEXICAL_UPPERCASE,
    )


def acronym_policy(language: str) -> AcronymRenderPolicy:
    """Return the maintained uppercase-token policy for a base language."""
    return _ACRONYM_POLICIES.get(base_language(language), _ACRONYM_POLICIES["en"])


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
class CodeToken:
    """One semantic token in an alphanumeric code."""

    kind: Literal["letters", "digits", "separator"]
    text: str


@dataclass(frozen=True, slots=True)
class CodeRenderPolicy:
    """Category-specific rendering policy for typed codes."""

    letters: Literal["grapheme", "spoken_letter_name", "lexical"] = "grapheme"
    digits: Literal["digitwise", "cardinal", "year"] = "digitwise"
    separators: Literal["omit", "speak", "pause"] = "omit"


_CODE_POLICIES = {
    "serial": CodeRenderPolicy("grapheme", "digitwise", "omit"),
    "vin": CodeRenderPolicy("grapheme", "digitwise", "omit"),
    "license": CodeRenderPolicy("grapheme", "digitwise", "omit"),
    "model": CodeRenderPolicy("grapheme", "cardinal", "omit"),
    "product": CodeRenderPolicy("grapheme", "digitwise", "omit"),
}


_ISBN_POLICIES = {
    "en": IsbnRenderPolicy("digitwise", "letters_and_kind"),
    "de": IsbnRenderPolicy("digitwise", "letters_and_kind"),
    "es": IsbnRenderPolicy("digitwise", "letters_and_kind", "grupo", True),
    "it": IsbnRenderPolicy("digitwise", "letters_and_kind", "gruppo", True),
    "fr": IsbnRenderPolicy("cardinal", "letters_and_kind", "groupe", True),
}


def _cardinal(value: int, language: str) -> str:
    rendered = str(num2words(value, lang=resolve_num2words_language(language)))
    if base_language(language) == "en":
        return rendered.replace(" and ", " ")
    return rendered


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
    return " ".join(parts)


def _ip_text(value: str, language: str) -> str:
    point = {"de": "Punkt", "es": "punto", "fr": "point", "it": "punto"}.get(
        base_language(language), "point"
    )
    return f" {point} ".join(_digitwise(part, language) for part in value.split("."))


def _fraction_text(whole: str | None, symbol: str, language: str) -> str:
    base = base_language(language)
    fraction = _FRACTIONS[symbol]
    fraction_text = _FRACTION_WORDS.get(base, _FRACTION_WORDS["en"]).get(fraction, symbol)
    if whole is None:
        return fraction_text
    connector = {"de": "und", "es": "y", "fr": "et", "it": "e"}.get(base, "and")
    return f"{_cardinal(int(whole), language)} {connector} {fraction_text}"


def _fraction_word(numerator: int, denominator: int, language: str) -> str:
    """Render a slash fraction with explicit, locale-aware morphology."""
    base = base_language(language)
    words = _DENOMINATOR_WORDS.get(base, _DENOMINATOR_WORDS["en"])
    denominator_word = words.get(denominator)
    if denominator_word is None:
        denominator_word = str(
            num2words(denominator, lang=resolve_num2words_language(language), to="ordinal")
        )
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
    if denominator_value <= 0 or numerator_value <= 0 or denominator_value > 99:
        return None
    fraction = _fraction_word(numerator_value, denominator_value, language)
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


def _contextual_roman_text(value: str, context: str, language: str) -> str:
    number = _roman_value(value)
    base = base_language(language)
    ordinal = any(
        word in context.casefold()
        for word in ("century", "siglo", "siècle", "secolo", "king", "queen", "pope")
    )
    rendered = str(
        num2words(
            number,
            lang=resolve_num2words_language(language),
            to="ordinal" if ordinal else "cardinal",
        )
    )
    if base == "de" and any(word in context.casefold() for word in ("king", "queen", "pope")):
        return f"der {rendered[:1].upper()}{rendered[1:]}"
    return rendered


def _literal_text(value: str, language: str) -> str:
    """Render URL/e-mail/version punctuation without generic number stages."""
    return render_sequence(value.rstrip(".,;:!?"), language=language)


def _phone_text(value: str, language: str) -> str:
    """Render phone groups without speaking ordinary separator punctuation."""
    policy = _PHONE_POLICIES.get(base_language(language), _PHONE_POLICIES["en"])
    groups = tuple(re.findall(r"\d+", value))
    rendered: list[str] = []
    if value.lstrip().startswith("+"):
        rendered.append(policy.plus_word)
    for group in groups:
        if policy.preserve_leading_zero and group.startswith("0"):
            rendered.append(_digitwise(group, language))
        elif policy.group_mode == "cardinal":
            rendered.append(_cardinal(int(group), language))
        elif policy.group_mode == "two_digit_cardinal" and len(group) == 2:
            rendered.append(_cardinal(int(group), language))
        else:
            rendered.append(_digitwise(group, language))
    return " ".join(rendered)


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
    if marker == "#":
        rendered = value
    elif marker == "@" and value.isascii() and value.islower() and len(value) <= 8:
        rendered = _grapheme_text(value, language)
    else:
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
        "#": {"_": "drop", "-": "space"},
        "@": {"_": "space", "-": "space"},
    }
    for index, (kind, token) in enumerate(tokens):
        if kind == "digit":
            if len(token) == 4 and 1900 <= int(token) <= 2100:
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
            mode = separator_modes.get(marker, {}).get(token, "speak")
            if mode == "drop":
                continue
            if mode == "space":
                rendered.append(
                    vocabulary(language).underscore if token == "_" and marker == "@" else " "
                )
            else:
                rendered.append(
                    vocabulary(language).underscore if token == "_" else vocabulary(language).hyphen
                )
        elif marker == "@" and token.isascii() and token.islower() and len(token) <= 4:
            rendered.append(_grapheme_text(token, language))
        elif opaque and token.isascii() and token.isupper():
            rendered.append(render_letters(token, language=language))
        else:
            rendered.append(token)
    return " ".join(rendered)


def _formula_is_plausible(value: str) -> bool:
    tokens = re.findall(r"[A-Z][a-z]?", value)
    return (
        all(token in _ELEMENT_SYMBOLS for token in tokens)
        and (len(tokens) >= 2 or bool(re.search(r"[0-9₀-₉]", value)))
        and bool(re.search(r"[a-z]", value) or re.search(r"[0-9₀-₉]", value))
    )


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
                vocabulary(language).open_paren
                if token == "("
                else vocabulary(language).close_paren
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
    for token in re.findall(r"\d+(?:[.,]\d+)?|[A-Za-z]+|√|[()⁰¹²³⁴⁵⁶⁷⁸⁹]|[+−*=×÷<>^-]", value):
        if token.isdigit():
            parts.append(_cardinal(int(token), language))
        elif re.fullmatch(r"\d+[.,]\d+", token):
            parts.append(_decimal_text(token, language, context="math"))
        elif token == "√":
            parts.append(roots.get(base_language(language), roots["en"]))
        elif token in "()":
            parts.append(
                vocabulary(language).open_paren
                if token == "("
                else vocabulary(language).close_paren
            )
        elif token in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            parts.append(
                _cardinal(int(token.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))), language)
            )
        elif token.isalpha():
            parts.append(render_letters(token, language=language) if len(token) <= 2 else token)
        else:
            parts.append(operators[token])
    return " ".join(parts)


def _math_is_plausible(value: str, text: str, start: int) -> bool:
    """Require mathematical context before treating code hyphens as minus."""
    if re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+", value):
        return False
    prefix = text[max(0, start - 48) : start]
    if re.search(
        r"\b(?:serial|sku|model|product|part|code|id|matricola|plate)\s*[:#-]?\s*$",
        prefix,
        re.IGNORECASE,
    ):
        return False
    return bool(re.search(r"[+*=×÷<>^]|\s[-−]\s", value))


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


def _typed_code_text(value: str, language: str, *, category: str = "product") -> str:
    policy = _CODE_POLICIES.get(category, _CODE_POLICIES["product"])
    parts: list[str] = []
    for token in _code_tokens(value):
        if token.kind == "digits":
            if policy.digits == "cardinal":
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
        elif policy.separators == "pause":
            parts.append(" ")
    return " ".join(part for part in parts if part.strip())


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
        return f" {separator} ".join(rendered)
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


def _acronym_text(value: str, language: str) -> str:
    policy = acronym_policy(language)
    if value in policy.lexical_words:
        if policy.lexical_case == "source-preserving":
            return value
        if policy.lexical_case == "lower":
            return value.casefold()
        return value[:1].upper() + value[1:].casefold()
    if value in policy.preserve:
        return value
    alpha_mode = policy.default_mode if value in policy.initialisms else "grapheme_spaced"
    return render_sequence(
        value,
        language=language,
        policy=SequenceRenderPolicy(alpha_mode=alpha_mode),
    )


def _score_text(value: str, language: str) -> str:
    match = re.fullmatch(r"\s*(\d+)\s*(?::|[-–]|a|to|à)\s*(\d+)\s*", value, re.IGNORECASE)
    if match is None:
        return value
    left, right = match.groups()
    connector = {"de": "zu", "es": "a", "fr": "à", "it": "a"}.get(base_language(language), "to")
    return f"{_cardinal(int(left), language)} {connector} {_cardinal(int(right), language)}"


def _legal_text(value: str, language: str) -> str:
    base = base_language(language)
    label_match = re.fullmatch(
        r"(section|sec\.?|article|art\.?|chapter|chap\.?)\s*(\d+)(?:\s+(?:subsection|paragraph|para\.?|§)\s*(\d+))?",
        value,
        re.IGNORECASE,
    )
    if label_match:
        headings = {
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
        key = label_match.group(1).casefold().rstrip(".")
        heading = headings.get(base, {}).get(key, key)
        result = f"{heading} {_cardinal(int(label_match.group(2)), language)}"
        if label_match.group(3):
            result += f" {_cardinal(int(label_match.group(3)), language)}"
        return result
    german_match = re.fullmatch(r"§\s*(\d+)(?:\s+Abs\.?\s*(\d+))?\s+([A-ZÄÖÜ]{2,})", value)
    if german_match:
        result = f"Paragraf {_cardinal(int(german_match.group(1)), language)}"
        if german_match.group(2):
            result += f" Absatz {_cardinal(int(german_match.group(2)), language)}"
        result += f" {render_sequence(german_match.group(3), language=language)}"
        return result
    german_roman_match = re.fullmatch(
        r"§\s*(\d+)\s+([IVXLCDM]+)(?:\s+(\d+))?\s+([A-ZÄÖÜ]{2,})", value
    )
    if german_roman_match:
        subsection = _roman_value(german_roman_match.group(2))
        result = (
            f"Paragraf {_cardinal(int(german_roman_match.group(1)), language)} "
            f"Absatz {_cardinal(subsection, language)}"
        )
        if german_roman_match.group(3):
            result += f" Satz {_cardinal(int(german_roman_match.group(3)), language)}"
        return f"{result} {render_sequence(german_roman_match.group(4), language=language)}"
    us_match = re.fullmatch(r"(\d+)\s+U\.S\.C\.\s+§\s*(\d+)", value, re.IGNORECASE)
    if us_match:
        left = _cardinal(int(us_match.group(1)), language).replace("-", " ").replace(",", "")
        right = _cardinal(int(us_match.group(2)), language).replace("-", " ").replace(",", "")
        return f"{left} U S C section {right}"
    es_match = re.fullmatch(r"ley\s+(\d{1,3}(?:\.\d{3})?)", value, re.IGNORECASE)
    if es_match:
        return f"ley {_cardinal(int(es_match.group(1).replace('.', '')), language)}"
    it_match = re.fullmatch(r"legge\s+n\.?\s*(\d+)(?:/(\d{4}))?", value, re.IGNORECASE)
    if it_match:
        result = f"legge numero {_cardinal(int(it_match.group(1)), language)}"
        if it_match.group(2):
            result += f" del {_cardinal(int(it_match.group(2)), language)}"
        return result
    fr_match = re.fullmatch(r"(?:décret|decret)\s+n[°o]?\s*(\d{4})-(\d+)", value, re.IGNORECASE)
    if fr_match:
        return f"décret numéro {_cardinal(int(fr_match.group(1)), language)} {_cardinal(int(fr_match.group(2)), language)}"
    prefix_match = re.fullmatch(
        r"([A-ZÄÖÜ]{2,})\s+§\s*(\d+)(?:\s+Abs\.?\s*(\d+))?", value, re.IGNORECASE
    )
    if prefix_match:
        result = f"{_digitwise(prefix_match.group(1), language)} Paragraf {_cardinal(int(prefix_match.group(2)), language)}"
        if prefix_match.group(3):
            result += f" Absatz {_cardinal(int(prefix_match.group(3)), language)}"
        return result
    match = re.match(
        r"(?:§|Art\.?|Artikel)\s*(\d+)(?:\s+([IVXLCDM]+))?(?:\s+(\d+))?\s+([A-ZÄÖÜ]{2,})$",
        value,
        re.IGNORECASE,
    )
    if not match:
        return render_sequence(value, language=language)
    headings = {
        "cs": ("paragraf", "článek"),
        "de": ("Paragraf", "Artikel"),
        "en": ("section", "article"),
        "es": ("párrafo", "artículo"),
        "fr": ("paragraphe", "article"),
        "it": ("paragrafo", "articolo"),
        "pt": ("parágrafo", "artigo"),
    }
    heading_pair = headings.get(base, headings["en"])
    heading = heading_pair[0] if value.lstrip().startswith("§") else heading_pair[1]
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
) -> None:
    if _claimed(match.start(), match.end(), protected):
        specificity = {
            "sequence.biology": 20,
            "sequence.formula": 20,
            "sequence.isbn": 30,
            "sequence.product": 15,
            "sequence.plate": 15,
            "sequence.math": 5,
        }.get(rule, 0)
        candidates.append(
            Replacement(
                match.start(), match.end(), value, "structured", language, rule, specificity
            )
        )


def iter_sequence_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
) -> tuple[Replacement, ...]:
    """Recognize and render high-confidence atomic structured sequences."""
    language = normalize_language(language)
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    for pattern, rule in ((_URL_RE, "sequence.url"), (_EMAIL_RE, "sequence.email")):
        for match in pattern.finditer(text):
            _add(
                candidates,
                match,
                _literal_text(match.group(0), language),
                language,
                rule,
                protected,
            )
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
        value = _slash_fraction_text(match["whole"], numerator, denominator, language)
        if value is not None:
            _add(candidates, match, value, language, "sequence.fraction", protected)
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
        if (
            not blocked
            and not _looks_like_date_shape(match["value"])
            and _phone_is_plausible(match["value"])
        ):
            _add(
                candidates,
                match,
                _phone_text(match["value"], language),
                language,
                "sequence.phone",
                protected,
            )
    for match in _EMERGENCY_RE.finditer(text):
        _add(
            candidates,
            match,
            match.group(0).replace(match["value"], _cardinal(int(match["value"]), language)),
            language,
            "sequence.emergency",
            protected,
        )
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
                    _literal_text(value, language),
                    "structured",
                    language,
                    "sequence.version",
                )
            )
    for match in _VERSION_RE.finditer(text):
        prefix = text[max(0, match.start() - 32) : match.start()]
        contextual = bool(
            re.search(r"\b(?:version|release|ver\.?|build)\s*[=:]?\s*$", prefix, re.IGNORECASE)
        )
        if promote_literals or not contextual:
            _add(
                candidates,
                match,
                _literal_text(match["value"], language),
                language,
                "sequence.version",
                protected,
            )
    for match in _ROMAN_CONTEXT_RE.finditer(text):
        if not _roman_is_valid(match["value"]):
            continue
        start, end = match.span("value")
        if _claimed(start, end, protected):
            candidates.append(
                Replacement(
                    start,
                    end,
                    _contextual_roman_text(match["value"], match["context"], language),
                    "structured",
                    language,
                    "sequence.roman",
                )
            )
    for pattern in (_ROMAN_YEAR_RE,):
        for match in pattern.finditer(text):
            if _roman_is_valid(match["value"]):
                start, end = match.span("value")
                if _claimed(start, end, protected):
                    candidates.append(
                        Replacement(
                            start,
                            end,
                            _contextual_roman_text(match["value"], match["context"], language),
                            "structured",
                            language,
                            "sequence.roman",
                        )
                    )
    for match in _MONARCH_RE.finditer(text):
        if _roman_is_valid(match["value"]):
            start, end = match.span("value")
            if _claimed(start, end, protected):
                ordinal = str(
                    num2words(
                        _roman_value(match["value"]),
                        lang=resolve_num2words_language(language),
                        to="ordinal",
                    )
                )
                rendered = (
                    f"der {ordinal[:1].upper()}{ordinal[1:]}"
                    if base_language(language) == "de"
                    else f"the {ordinal}"
                )
                candidates.append(
                    Replacement(start, end, rendered, "structured", language, "sequence.roman")
                )
    for pattern, marker, rule in (
        (_HASHTAG_RE, "#", "sequence.hashtag"),
        (_MENTION_RE, "@", "sequence.mention"),
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
    for match in _MATH_RE.finditer(text):
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
        if _formula_is_plausible(match["value"]):
            _add(
                candidates,
                match,
                _formula_text(match["value"], language),
                language,
                "sequence.formula",
                protected,
            )
    for match in _TICKER_RE.finditer(text):
        value = f"dollar {render_sequence(match['value'], language=language)}"
        _add(candidates, match, value, language, "sequence.ticker", protected)
    for match in _PRODUCT_RE.finditer(text):
        raw_value = match["value"]
        if not re.search(r"\d|[A-ZÄÖÜÀ-Ý]|[-]", raw_value):
            continue
        raw_label = match["label"].strip()
        label_key = raw_label.casefold().replace(".", "")
        label_words = {
            "sn": "serial number",
            "s/n": "serial number",
            "serial": "serial number",
            "serial number": "serial number",
            "sku": "SKU",
            "vin": "VIN",
            "imei": "IMEI",
            "iccid": "ICCID",
            "model": "model",
            "modelo": "modelo",
            "part": "part number",
            "part number": "part number",
            "product": "product code",
            "product code": "product code",
        }
        label = label_words.get(label_key, raw_label)
        category = (
            "vin"
            if label_key == "vin"
            else "serial"
            if label_key in {"sn", "s/n", "serial", "serial number"}
            else "model"
            if label_key in {"model", "modelo"}
            else "product"
        )
        value = _typed_code_text(match["value"], language, category=category)
        label = (
            _grapheme_text(label, language)
            if label in {"SKU", "VIN", "IMEI", "ICCID", "PIN"}
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
        _add(
            candidates,
            match,
            _typed_code_text(match["value"], language, category="product"),
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
    for match in _ACRONYM_RE.finditer(text):
        value = match["value"]
        policy = acronym_policy(language)
        if (
            value in policy.lexical_words
            or value in policy.initialisms
            or (
                value not in policy.preserve
                and len(value) <= 6
                and not _ROMAN_ONLY.fullmatch(value)
            )
        ):
            _add(
                candidates,
                match,
                _acronym_text(value, language),
                language,
                "sequence.acronym",
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
            if base_language(language) in {"en", "fr"}
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
                num2words(
                    int(match["number"]),
                    lang=resolve_num2words_language(language),
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
    return tuple(candidates)


__all__ = ["iter_sequence_replacements"]
