"""
Tempe Torch — Unified Live Score Fetcher

This script pulls live scores across multiple sports and outputs a
normalized JSON file used by the Tempe Torch newspaper frontend.

Designed to run inside GitHub Actions daily.
"""

import json
import requests
from datetime import datetime

OUTPUT_PATH = "data/daily_scores.json"


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def fetch_json(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Fetch failed: {url} -> {e}")
        return None


# --------------------------------------------------
# ESPN SCOREBOARD FETCHERS
# --------------------------------------------------


def parse_espn_scoreboard(data, sport_label):
    games = []

    if not data or "events" not in data:
        return games

    for event in data["events"]:
        try:
            comp = event["competitions"][0]
            teams = comp["competitors"]

            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")

            status = comp["status"]["type"]["description"]

            games.append(
                {
                    "sport": sport_label,
                    "home": home["team"]["displayName"],
                    "away": away["team"]["displayName"],
                    "home_score": home.get("score"),
                    "away_score": away.get("score"),
                    "status": status,
                }
            )
        except Exception:
            continue

    return games


# --------------------------------------------------
# SPORT FETCH FUNCTIONS
# --------------------------------------------------


def fetch_nfl():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    data = fetch_json(url)
    return parse_espn_scoreboard(data, "NFL")


def fetch_ncaa_basketball():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    data = fetch_json(url)
    return parse_espn_scoreboard(data, "NCAA Basketball")


def fetch_ncaa_softball():
    url = "https://site.api.espn.com/apis/site/v2/sports/softball/college-softball/scoreboard"
    data = fetch_json(url)
    return parse_espn_scoreboard(data, "College Softball")


# --------------------------------------------------
# Cricket (basic placeholder via ESPN Cricinfo JSON)
# --------------------------------------------------


def fetch_cricket():
    url = "https://site.api.espncricinfo.com/apis/site/v2/sports/cricket/scoreboard"
    data = fetch_json(url)

    games = []

    if not data or "events" not in data:
        return games

    for event in data["events"]:
        try:
            comp = event["competitions"][0]
            teams = comp["competitors"]

            games.append(
                {
                    "sport": "Cricket",
                    "home": teams[0]["team"]["displayName"],
                    "away": teams[1]["team"]["displayName"],
                    "home_score": teams[0].get("score"),
                    "away_score": teams[1].get("score"),
                    "status": comp["status"]["type"]["description"],
                }
            )
        except Exception:
            continue

    return games


# --------------------------------------------------
# MAIN
# --------------------------------------------------


def main():
    print("Fetching live sports data...")

    all_games = []

    all_games.extend(fetch_nfl())
    all_games.extend(fetch_ncaa_basketball())
    all_games.extend(fetch_ncaa_softball())
    all_games.extend(fetch_cricket())

    output = {
        "updated": datetime.utcnow().isoformat(),
        "games": all_games,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(all_games)} games -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
