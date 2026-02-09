"""
Tempe Torch — Monday Edition Generator
Detailed "Day After" analysis and "Game Day" previews.
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- MONDAY EDITION CONTENT ---

PINNED_STORIES = [
    {
        "id": "sb-recap-main",
        "type": "lead", 
        "sport": "NFL • Super Bowl LX",
        "headline": "DEFENSE REIGNS SUPREME",
        "subhead": "Seahawks dismantle Patriots 29-13; Macdonald's scheme suffocates Maye to capture franchise's second title.",
        "dateline": "SANTA CLARA, Calif.",
        "body": """The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that suffocated the league's highest-flying offense, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX.

It wasn't the shootout pundits predicted. Instead, Mike Macdonald's defense turned Drake Maye's dream season into a nightmare. The Seahawks sacked the Patriots' sophomore quarterback seven times, holding New England to a season-low 240 total yards.

"We heard the noise," Macdonald said, clutching the Lombardi Trophy. "Everyone talked about their offense. Nobody talked about our front seven. I think they're talking now."

Sam Darnold, completing his remarkable career renaissance, was efficient and poised. He finished 22-of-28 for 215 yards and two touchdowns, avoiding the critical mistakes that once plagued him. His 15-yard strike to Jaxon Smith-Njigba in the third quarter opened up a 22-10 lead that feels insurmountable against this defense.

The turning point came late in the second quarter. Trailing 9-6, the Patriots drove to the Seattle 5-yard line. On 3rd-and-goal, Maye was swallowed up by Leonard Williams for a 12-yard sack. New England settled for a field goal, and Seattle responded with a methodical 75-yard touchdown drive—capped by a Kenneth Walker III run—to take control before the half.

Walker finished with 112 yards on the ground, wearing down a Patriots front that looked exhausted by the fourth quarter. As the clock hit zero, blue and green confetti fell, signaling the dawn of a new era in the NFC West.""",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": {
            "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
            "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
            "status": "FINAL"
        },
        "box_score": {
            "title": "Super Bowl LX Stats",
            "headers": ["Player", "Stats", "Impact"],
            "rows": [
                ["S. Darnold", "22/28, 2 TD", "Super Bowl MVP"],
                ["K. Walker", "22 car, 112 yds", "1 TD"],
                ["D. Maye", "18/41, 1 INT", "7 Sacks Taken"],
                ["SEA Def", "7 Sacks", "220 Yds Allowed"]
            ]
        }
    },
    {
        "id": "preview-suns-lakers",
        "type": "sidebar",
        "sport": "NBA • PREVIEW",
        "is_live": False,
        "headline": "Clash of Styles",
        "subhead": "Suns host Lakers in pivotal West matchup",
        "body": """Tonight at the Footprint Center (8:00 PM MST), two teams with opposing philosophies collide. The Suns (32-20) rely on mid-range efficiency, leading the league in shooting percentage from 10-16 feet (48%). The Lakers (30-22), conversely, live in the paint, averaging 58 points in the restricted area.

**The Matchup to Watch:** Anthony Davis vs. Jusuf Nurkic. In their last meeting, Nurkic's physicality forced Davis into a 6-for-19 shooting night. However, Davis has averaged 32 points since the All-Star break. If Phoenix doubles Davis, they leave themselves vulnerable to Austin Reaves and D'Angelo Russell on the perimeter.

**Stat of the Night:** The Suns are 18-2 when Devin Booker records 8+ assists. Ball movement will be key against a long Lakers defense.""",
        "game_data": {
            "home": "Suns", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png",
            "away": "Lakers", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png",
            "status": "TONIGHT 8:00 PM"
        },
        "box_score": {
            "title": "Team Comparison",
            "headers": ["Stat", "PHX", "LAL"],
            "rows": [
                ["PPG", "116.4", "115.8"],
                ["DEF RTG", "112.1", "113.5"],
                ["PACE", "98.5", "101.2"]
            ]
        }
    },
    {
        "id": "recap-asu-colo",
        "type": "sidebar", 
        "sport": "NCAA M.BB • ANALYSIS",
        "is_live": False,
        "headline": "Altitude Sickness",
        "subhead": "Fatigue, not talent, cost Devils in Boulder",
        "body": """Sunday's 78-70 loss wasn't a mystery; it was a metabolic failure. Advanced tracking data shows ASU's average defensive speed dropped by 18% in the final 8 minutes.

"We stopped cutting," Coach Hurley noted. "We settled for jumpers because we didn't have the legs to drive."

**The Breakdown:** With 3:12 left, ASU led 66-64. They proceeded to miss 5 straight shots—all jumpers. Colorado, meanwhile, attacked the rim on 6 consecutive possessions, drawing fouls on 4 of them. Until ASU builds the depth to rotate heavily at altitude, the mountain road trip will remain a graveyard.""",
        "game_data": {
            "home": "Colorado", "home_score": "78", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/38.png",
            "away": "Arizona St", "away_score": "70", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png",
            "status": "FINAL (SUN)"
        },
        "box_score": {
            "title": "Last 4 Minutes",
            "headers": ["Stat", "ASU", "COLO"],
            "rows": [
                ["FG", "1-8", "4-5"],
                ["Paint Pts", "2", "8"],
                ["FT Att", "0", "8"]
            ]
        }
    },
    {
        "id": "preview-nhl",
        "type": "grid",
        "sport": "NHL • PREVIEW",
        "headline": "Monday Night Hockey",
        "subhead": "Leafs' Power Play vs Habs' Discipline",
        "body": "Toronto (3rd in Atlantic) hosts Montreal (7th) in a classic rivalry. The key: Toronto's Power Play is operating at 28.5% (2nd in NHL), while Montreal takes the most minor penalties in the league (4.2 per game). If the Canadiens can't stay out of the box, Matthews and Marner will feast.",
        "game_data": {
            "home": "Leafs", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nhl/500/tor.png",
            "away": "Canadiens", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nhl/500/mtl.png",
            "status": "5:00 PM MST"
        },
        "box_score": {
            "title": "Special Teams",
            "headers": ["Unit", "TOR", "MTL"],
            "rows": [
                ["PP%", "28.5%", "16.2%"],
                ["PK%", "78.4%", "74.1%"]
            ]
        }
    },
    {
        "id": "recap-cricket",
        "type": "grid",
        "sport": "T20 WC • ANALYSIS",
        "headline": "SKY Saves India",
        "subhead": "Captain's knock averts disaster",
        "body": "At 34/4, India stared into the abyss. The USA seamers utilized the early moisture perfectly. But Suryakumar Yadav (84*) adjusted his game, abandoning his trademark scoops for ground strokes until the spinners arrived. His partnership with Pandya (32) was a masterclass in risk management.",
        "game_data": {
            "home": "India", "home_score": "161/9", "home_logo": "https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg",
            "away": "USA", "away_score": "132/8", "away_logo": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Flag_of_the_United_States.svg",
            "status": "FINAL (SUN)"
        },
        "box_score": None
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "68°F", "desc": "Morning clouds clearing to sun.", "high": "72", "low": "48"},
    "quote": {"text": "Nobody talked about our front seven. I think they're talking now.", "author": "Mike Macdonald"},
    "staff": ["Editor: R. Baral", "Analysis: The Armchair Team", "Photo: Getty Images"],
    "date": "Monday, February 9, 2026"
}

# --- LOGIC ---

def generate_live_narrative(game):
    """Generates simple stories for REAL live games fetched from ESPN"""
    home = game['home']
    away = game['away']
    sport = game['sport']
    
    headline = f"{away} vs {home}"
    body = f"Live coverage of {away} taking on {home} in {sport} action. Check back for post-game analysis."
    
    return {
        "id": f"live-{random.randint(1000,9999)}",
        "type": "grid", 
        "sport": sport,
        "headline": headline,
        "subhead": f"{game['status']} - {game['league']}",
        "body": body,
        "game_data": game, 
        "box_score": None 
    }

def main():
    # 1. Load Real Live Scores
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            for g in raw_data.get("games", []):
                # Filter out our pinned teams to avoid duplicates
                if g['home'] not in ["Suns", "Lakers", "Leafs", "Seahawks", "Colorado"]:
                    live_stories.append(generate_live_narrative(g))

    # 2. Merge Pinned + Live
    all_stories = PINNED_STORIES + live_stories

    output = {
        "meta": INSIDE_FLAP_DATA,
        "stories": all_stories
    }

    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated Monday Edition with {len(all_stories)} stories.")

if __name__ == "__main__":
    main()
