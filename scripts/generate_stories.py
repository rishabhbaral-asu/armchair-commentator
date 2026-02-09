"""
Tempe Torch — Hybrid Narrative Generator
Merges "Pinned" legacy stories with Live ESPN data.
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. PINNED CONTENT (The "2026" Portfolio Stories) ---
# These are treated as "Real" data objects by the frontend.

PINNED_STORIES = [
    {
        "id": "lead-bball-loss",
        "type": "lead", # determines layout position: 'lead', 'sidebar', 'grid'
        "sport": "NCAA Men's BB",
        "headline": "THIN AIR, THIN MARGINS",
        "subhead": "Devils collapse late in Boulder; Colorado closes on 12-4 run to spoil Odum's big night.",
        "dateline": "BOULDER, Colo.",
        "body": "The altitude in Boulder is undefeated, and for 36 minutes, the Arizona State Sun Devils (12-12, 3-8 Big 12) looked like they might be the exception. They held a three-point lead with four minutes remaining, silencing the CU Events Center. But gasping lungs and missed free throws eventually doomed them to a 78-70 loss against the Buffaloes.\n\nSenior point guard Moe Odum was electric, pouring in 23 points and dishing 5 assists. He repeatedly attacked Colorado's 7-foot interior, finding freshman center Massamba Diop (19 pts, 7 rebs) for easy dunks. But when the game tightened, Colorado's depth took over.",
        "image_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png", # Fallback logo
        "game_data": {
            "home": "Colorado", "home_score": "78", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/38.png",
            "away": "Arizona St", "away_score": "70", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png",
            "status": "FINAL"
        },
        "box_score": {
            "title": "Box Score: ASU vs Colorado",
            "headers": ["Player", "PTS", "REB", "AST"],
            "rows": [
                ["M. Odum", "23", "2", "5"],
                ["M. Diop", "19", "7", "1"],
                ["B. Ford", "12", "3", "2"],
                ["TOTAL", "70", "23", "10"]
            ]
        }
    },
    {
        "id": "sb-preview",
        "type": "special", # Special Super Bowl Banner
        "sport": "NFL",
        "headline": "Super Bowl LX",
        "subhead": "Kickoff at 4:30 PM. Complete coverage of Seahawks vs Patriots.",
        "body": "It is a battle of narratives as much as football. On one sideline stands Sam Darnold, the once-discarded prospect who found salvation in Seattle. Under Mike Macdonald's system, Darnold threw for 4,200 yards and 32 touchdowns this season.\n\nOpposite him is the future: Drake Maye. The Patriots' sophomore sensation has evoked memories of Brady, leading New England back to the promised land in just his second year.",
        "game_data": {
            "home": "Seahawks", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
            "away": "Patriots", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
            "status": "TODAY 4:30 PM"
        }
    },
    {
        "id": "live-minn-md",
        "type": "sidebar",
        "sport": "NCAA M.BB",
        "is_live": True,
        "headline": "Crunch Time",
        "subhead": "Stephens hits HUGE three",
        "body": "The Barn is shaking! Moments ago, Chance Stephens drilled a corner three—his fifth of the night—to reclaim the lead for Minnesota. The Gophers (11-12) now lead Maryland (8-14) 68-65 with just over a minute to play.\n\nThis has been a revenge game for the ages. Stephens, the former Maryland guard, has torched his old team for 17 points.",
        "game_data": {
            "home": "Minnesota", "home_score": "68", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/135.png",
            "away": "Maryland", "away_score": "65", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/120.png",
            "status": "LIVE (1:12 2nd)"
        },
        "box_score": {
            "title": "Live Leaders",
            "headers": ["Player", "Stat", "Val"],
            "rows": [
                ["Stephens", "PTS", "17"],
                ["Payne", "REB", "9"]
            ]
        }
    },
    {
        "id": "live-softball",
        "type": "sidebar",
        "sport": "Softball",
        "is_live": True,
        "headline": "Devils Lead Early",
        "subhead": "Windle doubles in the 2nd",
        "body": "The Sun Devils have wasted no time. After ace Aissa Silva struck out the side in the top of the 1st, the offense went to work. Senior Tanya Windle ripped a double down the left-field line, scoring two.",
        "game_data": {
            "home": "Arizona St", "home_score": "3", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png",
            "away": "Memphis", "away_score": "0", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/235.png",
            "status": "LIVE (Bot 2nd)"
        },
        "box_score": {
            "title": "Scorecard",
            "headers": ["Tm", "1", "2", "R", "H"],
            "rows": [
                ["MEM", "0", "0", "0", "0"],
                ["ASU", "0", "3", "3", "3"]
            ]
        }
    },
    {
        "id": "cricket-india",
        "type": "sidebar",
        "sport": "T20 WC",
        "headline": "SKY's The Limit",
        "subhead": "Yadav rescues India vs USA",
        "body": "The 2026 T20 World Cup nearly saw its biggest upset. Captain Suryakumar Yadav exploded for an unbeaten 84 off 48 balls to rescue India after a top-order collapse against the hosts in Mumbai.",
        "game_data": {
            "home": "India", "home_score": "161/9", "home_logo": "https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg",
            "away": "USA", "away_score": "132/8", "away_logo": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Flag_of_the_United_States.svg",
            "status": "FINAL"
        },
        "box_score": {
            "title": "Match Summary",
            "headers": ["Batter", "R", "B"],
            "rows": [
                ["S. Yadav", "84", "48"],
                ["M. Patel", "45", "38"]
            ]
        }
    },
    {
        "id": "hockey-stcloud",
        "type": "grid",
        "sport": "NCAA Hockey",
        "headline": "Berzins Robs Devils",
        "subhead": "38 saves deny comeback",
        "body": "St. Cloud State goalie Patriks Berzins turned away 38 shots to preserve a 4-3 victory for the Huskies. ASU pulled within one in the final minute but could not find the equalizer.",
        "game_data": {
            "home": "St Cloud", "home_score": "4", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2630.png",
            "away": "Arizona St", "away_score": "3", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png",
            "status": "FINAL"
        },
        "box_score": {
            "title": "Period Score",
            "headers": ["Tm", "1", "2", "3", "F"],
            "rows": [
                ["SCSU", "1", "3", "0", "4"],
                ["ASU", "0", "1", "2", "3"]
            ]
        }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "76°F", "desc": "Clear skies, light SW winds.", "high": "78", "low": "52"},
    "quote": {"text": "The altitude is undefeated.", "author": "Coach Hurley"},
    "staff": ["Editor: R. Baral", "Sports: The Armchair Team", "Photo: Getty Images"],
    "date": "Sunday, February 8, 2026"
}

# --- 2. LOGIC ---

def generate_live_narrative(game):
    """Generates simple stories for REAL live games fetched from ESPN"""
    home = game['home']
    away = game['away']
    sport = game['sport']
    
    # Simple template logic
    headline = f"{away} vs {home}"
    body = f"Full coverage of {away} taking on {home} in {sport} action."
    
    return {
        "id": f"live-{random.randint(1000,9999)}",
        "type": "grid", # Default live games go to the bottom grid
        "sport": sport,
        "headline": headline,
        "subhead": f"{game['status']} - {game['league']}",
        "body": body,
        "game_data": game, # Pass full ESPN data
        "box_score": None 
    }

def main():
    # 1. Load Real Live Scores
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            # Convert filtered live games into Story Objects
            for g in raw_data.get("games", []):
                # Only add if it's not a duplicate of our pinned stories (basic check)
                if g['home'] not in ["Colorado", "Minnesota", "Arizona St", "India", "Seahawks"]:
                    live_stories.append(generate_live_narrative(g))

    # 2. Merge Pinned + Live
    # We put pinned stories first so they take the "Prime" spots in the layout
    all_stories = PINNED_STORIES + live_stories

    output = {
        "meta": INSIDE_FLAP_DATA,
        "stories": all_stories
    }

    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(all_stories)} hybrid stories.")

if __name__ == "__main__":
    main()
