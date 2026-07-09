import pytest

from . import fmt


@pytest.mark.parametrize(
    ("text", "pattern"),
    [
        ("café", "cafe"),
        ("naïve", "naive"),
        ("façade", "facade"),
        ("résumé", "resume"),
        ("São Paulo", "Sao Paulo"),
        ("München", "Munchen"),
        ("crème brûlée", "creme brulee"),
        ("élève", "eleve"),
        ("coöperate", "cooperate"),
        ("smörgåsbord", "smorgasbord"),
    ],
)
def test_sub_diacritics(text: str, pattern: str):
    assert fmt.sub_diacritics(pattern, "[MATCH]", text) == "[MATCH]"


@pytest.mark.parametrize(
    ("title", "artist", "expected"),
    [
        # cSpell: disable
        (
            "ADELE 'Rolling In The Deep' (Studio Footage)",
            "Adele",
            "Rolling In The Deep",
        ),
        (
            "The Black Eyed Peas - I Gotta Feeling (Official Music Video)",
            "The Black Eyed Peas",
            "I Gotta Feeling",
        ),
        (
            "Lady Gaga - Just Dance (Official Music Video) ft. Colby O'Donis",
            "Lady Gaga feat. Colby O’Donis",
            "Just Dance",
        ),
        (
            "Carly Rae Jepsen - Call Me Maybe",
            "Carly Rae Jepsen",
            "Call Me Maybe",
        ),
        (
            "Rihanna - Umbrella (Orange Version) (Official Music Video) ft. JAŸ-Z",
            "Rihanna",
            "Umbrella",
        ),
        (
            "Amy Macdonald - This is the Life",
            "Amy Macdonald",
            "This is the Life",
        ),
        (
            "Bruno Mars - Grenade (Official Music Video)",
            "Bruno Mars",
            "Grenade",
        ),
        (
            "PSY - GANGNAM STYLE(강남스타일) M/V",
            "Psy",
            "GANGNAM STYLE",
        ),
        (
            "Britney Spears - ...Baby One More Time (Official Video)",
            "Britney Spears",
            "...Baby One More Time",
        ),
        (
            "MEHNERSMOOS & DRUNKEN MASTERS - Nachteule",
            "Mehnersmoos, Drunken Masters",
            "Nachteule",
        ),
        (
            "Queen – Bohemian Rhapsody (Official Video Remastered)",
            "Queen",
            "Bohemian Rhapsody",
        ),
        (
            "Green Day - 21 Guns [Official Music Video]",
            "Green Day",
            "21 Guns",
        ),
        (
            "a-ha - Take On Me (Official Video) [4K]",
            "a-ha",
            "Take On Me",
        ),
        (
            "The Beatles - The Beatles - Hey Jude (Official Music Video) [Remastered 2015]",
            "The Beatles",
            "Hey Jude",
        ),
        (
            "AnnenMayKantereit - Oft gefragt (Official Video)",
            "AnnenMayKantereit",
            "Oft gefragt",
        ),
        (
            "KRAFTKLUB - Schüsse in die Luft (official video)",
            "Kraftklub",
            "Schüsse in die Luft",
        ),
    ],
)
def test_clean_title(title: str, artist: str, expected: str):
    assert fmt.clean_title(title, artist) == expected
