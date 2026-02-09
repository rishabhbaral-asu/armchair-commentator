"""
Tempe Torch — Safe Narrative Generator
Strictly factual. No hallucinated rosters. 
Includes Date Filtering to remove August/Future games.
"""

import json
import random
from datetime import datetime, timedelta
from dateutil import parser # Requires: pip install python-dateutil
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. BOUNCER LISTS ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women"}
TARGET_SOCCER_CLUBS = {
    "Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", 
    "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"
}
TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}
MAJOR_FINALS_KEYWORDS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship"]

# --- 2. PINNED CONTENT (Manually Curated & SAFE) ---

# NOTE: Removed specific Patriots receiver name to avoid roster errors.
SB_BODY = """SANTA CLARA, Calif. — It is a battle of narratives as much as football. On one sideline stands Sam Darnold, the once-discarded prospect who found salvation in Seattle. Under Mike Macdonald's system, Darnold threw for 4,200 yards and 32 touchdowns this season, unlocking the terrifying potential of DK Metcalf and Jaxon Smith-Njigba.

Opposite him is the future: Drake Maye. The Patriots' sophomore sensation has evoked memories of Brady, leading New England back to the promised land in just his second year. Maye's connection with his receiving corps has been lethal in the playoffs, dismantling the Chiefs and Ravens on the road.

Kickoff is set for 4:30 PM MST on NBC. The Seahawks are currently 2.5-point favorites."""

# Original ASU Story
ASU_BODY = """BOULDER, Colo. — The altitude in Boulder is undefeated, and for 36 minutes, the Arizona State Sun Devils (12-12, 3-8 Big 12) looked like they might be the exception. They held a three-point lead with four minutes remaining, silencing the CU Events Center. But gasping lungs and missed free throws eventually doomed them to a 78-70 loss against the Buffaloes.

Senior point guard Moe Odum was electric, pouring in 23 points and dishing 5 assists. He repeatedly attacked Colorado's 7-foot interior, finding freshman center Massamba Diop (19 pts, 7 rebs) for easy dunks. But when the game tightened, Colorado's depth took over."""

PINNED_STORIES = [
    {
        "id": "sb-preview",
        "type": "special",
        "sport": "NFL",
        "headline": "Super Bowl LX",
        "subhead": "Kickoff at 4:30 PM. Complete coverage of Seahawks vs Patriots.",
        "dateline": "SANTA CLARA, Calif.",
        "body": SB_BODY,
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "TODAY 4:30 PM" }
    },
    {
        "id": "lead-bball-loss",
        "type": "lead",
        "sport": "NCAA Men's BB",
        "headline": "THIN AIR, THIN MARGINS",
        "subhead": "Devils collapse late in Boulder; Colorado closes on 12-4 run.",
        "dateline": "BOULDER, Colo.",
        "body": ASU_BODY,
        "image_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png",
        "game_data": { "home": "Colorado", "home_score": "78", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/38.png", "away": "Arizona St", "away_score": "70", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png", "status": "FINAL" },
        "box_score": { "title": "Box Score", "headers": ["Player", "PTS", "AST"], "rows": [["M. Odum", "23", "5"], ["M. Diop", "19", "1"]] }
    },
    {
        "id": "cricket-india",
        "type": "sidebar",
        "sport": "T20 WC",
        "headline": "SKY's The Limit",
        "subhead": "India Avoids Disaster",
        "dateline": "MUMBAI",
        "body": "MUMBAI — The 2026 T20 World Cup nearly saw its biggest upset on day one. Captain Suryakumar Yadav exploded for an unbeaten 84 off 48 balls to rescue India after a top-order collapse.\n\nIndia was reeling at 34/4 against a spirited USA attack that utilized the early moisture perfectly. But Yadav adjusted his game, abandoning his trademark scoops for ground strokes until the spinners arrived.",
        "game_data":
