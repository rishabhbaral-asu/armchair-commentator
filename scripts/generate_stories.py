"""
Tempe Torch — Daily Story Generator (Preview + Detailed Stories)
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")


STATE_FILTER = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}

INTERNATIONAL_TEAMS = {
    "India",
    "India (W)",
    "USA",
    "USA (M)",
    "USA (W)",
}

CRICKET_LEAGUES = {"ICC", "IPL", "MLC"}

SOCCER_CLUBS = {
    "Fulham",
    "Leeds",
    "Leverkusen",
    "Gladbach",
    "Barcelona",
    "Real Madrid",
    "PSG",
}

SOCCER_COMPETITIONS = {
    "Premier League",
    "Bundesliga",
    "La Liga",
    "Ligue 1",
    "Liga F",
    "NWSL",
}


# --------------------------------------------------
# Filtering
# --------------------------------------------------


def game_is_relevant(g):
    home = g.get("home", "")
    away = g.get("away", "")
    league = g.get("league", "")
    state = g.get("state", "")

    if state in STATE_FILTER:
        return True

    if home in INTERNATIONAL_TEAMS or away in INTERNATIONAL_TEAMS:
        return True

    if league in CRICKET_LEAGUES:
        return True

    if league in SOCCER_COMPETITIONS and (
        home in SOCCER_CLUBS or away in SOCCER_CLUBS
    ):
        return True

    return False


# --------------------------------------------------
# Writing helpers (less templated)
# --------------------------------------------------

HEADLINE_PATTERNS_CLOSE = [
    "{winner} slip past {loser} in tense finish",
    "Late push lifts {winner} over {loser}",
    "{winner} survive scare against {loser}",
]

HEADLINE_PATTERNS_COMFORT = [
    "{winner} handle {loser} with authority",
    "{winner} in control throughout against {loser}",
    "Clinical showing sends {winner} past {loser}",
]

HEADLINE_PATTERNS_GENERIC = [
    "{home} and {away} meet in featured matchup",
    "Spotlight falls on {home}–{away} clash",
]


def realistic_headline(g):
    home, away = g["home"], g["away"]
    hs, as_ = g.get("home_score"), g.get("away_score")

    if hs is None or as_ is None:
        return random.choice(HEADLINE_PATTERNS_GENERIC).format(home=home, away=away)

    winner = home if int(hs) > int(as_) else away
    loser = away if winner == home else home
    margin = abs(int(hs) - int(as_))

    if margin <= 3:
        pattern = random.choice(HEADLINE_PATTERNS_CLOSE)
    else:
        pattern = random.choice(HEADLINE_PATTERNS_COMFORT)

    return pattern.format(winner=winner, loser=loser).capitalize()


def preview_paragraph(g):
    home, away = g["home"], g["away"]
    sport = g.get("sport", "competition")

    return (
        f"{away} faced {home} in {sport} play, a matchup that carried implications "
        "for momentum and positioning as the season continues to take shape."
    )


def detailed_story(g):
    home, away = g["home"], g["away"]
    hs, as_ = g.get("home_score"), g.get("away_score")
    sport = g.get("sport", "competition")

    if hs is None or as_ is None:
        return (
            f"The contest between {away} and {home} remained unresolved at publication time, "
            "with stretches of control traded across a competitive evening of play."
        )

    winner = home if int(hs) > int(as_) else away
    loser = away if winner == home else home

    return (
        f"In a result that reflected steady execution, {winner} defeated {loser} {hs}-{as_} in {sport} action. "
        "Control of tempo and efficiency in key moments ultimately separated the sides, "
        "continuing a run of form that could shape the weeks ahead."
    )


# --------------------------------------------------
# Main
# --------------------------------------------------


def main():
    if not SCORES_PATH.exists():
        raise FileNotFoundError("Run score fetcher first.")

    with open(SCORES_PATH) as f:
        games = json.load(f).get("games", [])

    games = [g for g in games if game_is_relevant(g)]

    if not games:
        output = {
            "updated": datetime.utcnow().isoformat(),
            "lead_headline": "Quiet Day Across Covered Competitions",
            "preview_story": "Limited action took place within the Tempe Torch coverage footprint.",
            "detailed_story": "Additional fixtures are expected to restore a fuller schedule in the coming days.",
        }
    else:
        lead = games[0]

        output = {
            "updated": datetime.utcnow().isoformat(),
            "lead_headline": realistic_headline(lead),
            "preview_story": preview_paragraph(lead),
            "detailed_story": detailed_story(lead),
        }

    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
