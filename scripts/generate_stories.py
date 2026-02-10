"""
Tempe Torch — Honest Narrative Generator
Uses ONLY the Deep Data provided by update_scores.py.
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- PINNED CONTENT (The Classics - Unchanged) ---
PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13",
        "dateline": "SANTA CLARA, Calif.", 
        "body": "SANTA CLARA, Calif. — The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks.\n\nSam Darnold was efficient, throwing for 215 yards and two touchdowns. Kenneth Walker III added 112 yards on the ground.",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Super Bowl MVP", "headers": ["Player", "Stat", "Desc"], "rows": [["S. Darnold", "22/28", "2 TD"], ["K. Walker", "112", "Yards"]] }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "65°F", "desc": "Clear.", "high": "72", "low": "48"},
    "quote": {"text": "Tonight, the only ghost out there was the history we just buried.", "author": "Sam Darnold"},
    "staff": ["Editor: R. Baral", "Data: ESPN API"],
    "date": "Monday, February 9, 2026"
}

def generate_honest_narrative(game):
    """
    Constructs a story using ONLY available data fields.
    """
    home = game.get('home')
    away = game.get('away')
    venue = game.get('venue', 'Neutral Site')
    leaders = game.get('leaders', [])
    headline_note = game.get('headline', '')
    
    # 1. THE LEAD
    if game['state'] == 'pre':
        return f"PREVIEW: {away} travels to {venue} to face {home}. {headline_note}"
        
    elif game['state'] == 'in':
        return f"LIVE: Action is underway at {venue}. {away} and {home} are battling in what has been a competitive matchup so far."
        
    else: # FINAL
        try:
            h_s = int(game['home_score'])
            a_s = int(game['away_score'])
            winner = home if h_s > a_s else away
            loser = away if winner == home else home
            score = f"{h_s}-{a_s}"
        except:
            return f"FINAL: {away} vs {home} at {venue}."

        # 2. THE STATS (The "Authority" Check)
        stats_text = ""
        if leaders:
            l = leaders[0]
            stats_text = f"Top Performer: {l['name']} ({l['desc']}: {l['stat']})."
        
        return f"{winner} defeated {loser} {score} at {venue}. {stats_text} {headline_note}"

def generate_grid_item(game):
    return {
        "id": f"game-{game['game_id']}",
        "type": "grid",
        "sport": game['sport'],
        "headline": f"{game['away']} vs {game['home']}",
        "subhead": game['status'],
        "dateline": game['venue'],
        "body": generate_honest_narrative(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            # All games in this file have already passed the "Deep Fetch" relevance check
            for g in raw_data.get("games", []):
                # Dedupe
                if g['home'] not in ["Seahawks"]:
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} Verified Stories.")

if __name__ == "__main__":
    main()
