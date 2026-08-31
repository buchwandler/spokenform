from __future__ import annotations

from spokenform import (
    PreparationConfig,
    add_abbreviation,
    has_abbreviation,
    prepare,
    remove_abbreviation,
    reset_abbreviations,
)

ABBREVIATION_ONLY = PreparationConfig(
    language="en",
    expand_structured=False,
    expand_numbers=False,
    normalize_whitespace=False,
    use_spacy=False,
)

EN_ABBREVIATION_CASES = (
    ("Prof. Smith teaches math", "Professor Smith teaches math"),
    ("Dr. Johnson is here", "Doctor Johnson is here"),
    ("Rev. Martin spoke", "Reverend Martin spoke"),
    ("Mr. Anderson called", "Mister Anderson called"),
    ("Mrs. Wilson arrived", "Missus Wilson arrived"),
    ("Ms. Taylor is ready", "Miss Taylor is ready"),
    ("Lt. Davis reported", "Lieutenant Davis reported"),
    ("Gen. Patton led", "General Patton led"),
    ("Col. Sanders founded", "Colonel Sanders founded"),
    ("Capt. Kirk commands", "Captain Kirk commands"),
    ("Sgt. York was brave", "Sergeant York was brave"),
    ("See you Mon. morning", "See you Monday morning"),
    ("Meeting on Tue. at 3", "Meeting on Tuesday at 3"),
    ("Tues. is busy", "Tuesday is busy"),
    ("Wed. schedule", "Wednesday schedule"),
    ("Thu. deadline", "Thursday deadline"),
    ("TGIF! Fri. party", "TGIF! Friday party"),
    ("Sat. brunch", "Saturday brunch"),
    ("Sun. service", "Sunday service"),
    ("Born in Jan. 1990", "Born in January 1990"),
    ("Feb. 14 is Valentine's", "February 14 is Valentine's"),
    ("Mar. madness", "March madness"),
    ("Apr. showers", "April showers"),
    ("Sep. 11 memorial", "September 11 memorial"),
    ("Sept. is lovely", "September is lovely"),
    ("Oct. Halloween", "October Halloween"),
    ("Nov. election", "November election"),
    ("Dec. holidays", "December holidays"),
    ("123 Main St. is here", "123 Main Street is here"),
    ("St. Peter was", "Saint Peter was"),
    ("St. Patrick's Day", "Saint Patrick's Day"),
    ("Park Ave. apartment", "Park Avenue apartment"),
    ("Oak Rd. closed", "Oak Road closed"),
    ("Sunset Blvd. famous", "Sunset Boulevard famous"),
    ("Apt. 5B available", "Apartment 5B available"),
    ("Meeting at 9 A.M. today", "Meeting at 9 A M today"),
    ("Dinner at 7 P.M. sharp", "Dinner at 7 P M sharp"),
    ("Year 2024 A.D. now", "Year 2024 A D now"),
    ("500 B.C. ancient", "500 B C ancient"),
    ("She has a Ph.D. degree", "She has a P H D degree"),
    ("John Smith, M.D. practices", "John Smith, M D practices"),
    ("Earned a B.A. last year", "Earned a B A last year"),
    ("Martin Luther King Jr. spoke", "Martin Luther King Junior spoke"),
    ("John Doe Sr. retired", "John Doe Senior retired"),
    ("Apples, oranges, etc. are fruits", "Apples, oranges, et cetera are fruits"),
    ("Team A vs. Team B", "Team A versus Team B"),
    ("Fruits, e.g. apples", "Fruits, for example apples"),
    ("One apple, i.e. the red one", "One apple, that is the red one"),
    ("No.", "No."),
    ("He said No.", "He said No."),
    ("10.0 in. long", "10.0 inch long"),
    ("Check in.", "Check in."),
    ("Log in. Now.", "Log in. Now."),
    ("He is 6 ft. tall", "He is 6 foot tall"),
    ("Ft. Lauderdale is sunny", "Ft. Lauderdale is sunny"),
    ("Add 8 oz. of sugar", "Add 8 ounce of sugar"),
    ("Wizard of Oz.", "Wizard of Oz."),
    ("A 2 lb. bag", "A 2 pound bag"),
    ("lb. is a unit", "lb. is a unit"),
    ("prof. smith teaches", "Professor smith teaches"),
    ("Prof. Smith teaches", "Professor Smith teaches"),
    ("dr. jones", "Doctor jones"),
    ("Dr. Jones", "Doctor Jones"),
    ("See Dr. Smith, please.", "See Doctor Smith, please."),
    ("Meeting Mon. at noon!", "Meeting Monday at noon!"),
    ("He has a Ph.D.", "He has a P H D"),
    ("On Mon., we meet", "On Monday, we meet"),
    ("123 Main St.", "123 Main Street"),
    ("456 Oak St. is here", "456 Oak Street is here"),
)


def test_legacy_english_abbreviation_pairs() -> None:
    for source, expected in EN_ABBREVIATION_CASES:
        assert prepare(source, config=ABBREVIATION_ONLY).spoken_text == expected, source


STREET_CONTEXTS = (
    "123 Main St.",
    "456 Oak St. is here",
    "100 N. Elm St.",
    "456 S Oak St.",
    "I live at 5 Park St.",
    "The shop on 5th St.",
)
SAINT_CONTEXTS = (
    "St. Patrick's Day",
    "St. Peter was an apostle",
    "The church of St. John",
    "St. Mary church",
    "Visit St. Louis",
    "St. Paul, Minnesota",
    "St. Petersburg is beautiful",
    "St. Augustine, Florida",
    "St. John's Church",
    "Born in 1850, St. Peter was influential",
    "St. Patrick celebrated his 50th birthday",
    "Move to St. Paul, MN 55101",
    "Visit 123 St. Louis Avenue",
    "I live on St. Patrick Street",
    "St. John, apartment 5",
    "123 N. St. Mary's Rd.",
    "St. Christopher",
    "Visit St.",
)


def test_street_contexts_never_become_saints() -> None:
    for source in STREET_CONTEXTS:
        result = prepare(source, config=ABBREVIATION_ONLY).spoken_text
        assert "Street" in result
        assert "Street Peter" not in result


def test_saint_contexts_never_become_streets() -> None:
    for source in SAINT_CONTEXTS:
        result = prepare(source, config=ABBREVIATION_ONLY).spoken_text
        assert "Saint" in result
        assert "Street " not in result


GUARDED_FALSE_POSITIVES = (
    "Literally because the thing was so big, and because multiple intel sources suggested it would be difficult to move around in.",
    "wandering around in.",
    "Wizard of Oz.",
    "Ft. Lauderdale",
    "The answer was no.",
    "Open the window to let the air in.",
    "Use version2 in. docs.",
    "ModelX5 in.",
    "5\nin.",
    "No.7",
    "No.\n7",
    "Vol.\n7",
)


def test_guarded_abbreviations_fail_closed() -> None:
    for source in GUARDED_FALSE_POSITIVES:
        assert prepare(source, config=ABBREVIATION_ONLY).spoken_text == source


def test_guarded_abbreviations_accept_same_line_numeric_context() -> None:
    for source, expected in (
        ("No. 7", "number 7"),
        ("Vol.\t7", "volume\t7"),
        ("5 in.", "5 inch"),
        ("10.0 ft.", "10.0 foot"),
        ("30,000.10 oz.", "30,000.10 ounce"),
        (".5 lb.", ".5 pound"),
    ):
        assert prepare(source, config=ABBREVIATION_ONLY).spoken_text == expected


def test_custom_abbreviation_public_lifecycle() -> None:
    reset_abbreviations("en")
    try:
        add_abbreviation("Drx.", "Doctor extra", language="en")
        assert has_abbreviation("Drx.", language="en")
        assert prepare("Drx.", config=ABBREVIATION_ONLY).spoken_text == "Doctor extra"
        assert prepare("Drx.", config=ABBREVIATION_ONLY).spoken_text == "Doctor extra"
        assert remove_abbreviation("Drx.", language="en") is True
        assert remove_abbreviation("Drx.", language="en") is False
        assert not has_abbreviation("Drx.", language="en")
    finally:
        reset_abbreviations("en")


def test_custom_abbreviation_case_and_language_isolation() -> None:
    reset_abbreviations()
    try:
        add_abbreviation("ABC", "letters", language="en", case_sensitive=True)
        assert prepare("ABC", config=ABBREVIATION_ONLY).spoken_text == "letters"
        assert prepare("abc", config=ABBREVIATION_ONLY).spoken_text == "abc"
        add_abbreviation("Drx.", "Docter extra", language="de")
        assert prepare("Drx.", config=ABBREVIATION_ONLY).spoken_text == "Drx."
    finally:
        reset_abbreviations()


def test_custom_abbreviation_punctuation_boundaries() -> None:
    assert prepare("(Dr.) Smith", config=ABBREVIATION_ONLY).spoken_text == "(Doctor) Smith"
    assert prepare('He said "etc."', config=ABBREVIATION_ONLY).spoken_text == 'He said "et cetera"'
    assert prepare("Dr.foo", config=ABBREVIATION_ONLY).spoken_text == "Dr.foo"
