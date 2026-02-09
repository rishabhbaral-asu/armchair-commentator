"""
Tempe Torch — Story Generator & Filter
Filters the raw scores and fetches REAL news headlines.
"""

import json
import requests
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- CONFIGURATION: WHO TO TRACK ---
STATE_FILTER = ["CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"]

INTERNATIONAL_TEAMS = ["India", "USA", "United States"]

CRICKET_LEAGUES = ["ICC", "IPL", "MLC", "Major League Cricket", "Indian Premier League"]

SOCCER_CLUBS = [
    "Fulham", "Leeds", "Leverkusen", "Gladbach", "St. Pauli",
    "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"
]

# --------------------------------------------------
# LOGIC
# --------------------------------------------------

def game_is_relevant(g):
    # 1. Check Cricket Leagues
    if g['sport'] == "Cricket":
        # Check if league name matches (often embedded in game info, but we'll check team names/locations too)
        # Since we don't have league name easily in all objects, we rely on teams.
        pass 

    # 2. Check Locations (States)
    # We look for " Tempe, AZ" or similar in the location string
    for state in STATE_FILTER:
        if (state in g['home_location']) or (state in g['away_location']):
            return True

    # 3. Check Specific Teams (Intl & Soccer Clubs)
    targets = INTERNATIONAL_TEAMS + SOCCER_CLUBS
    for t in targets:
        if t.lower() in g['home'].lower() or t.lower() in g['away'].lower():
            return True
            
    # 4. Check Cricket specifically for leagues if possible or just assume all cricket is good? 
    # The prompt asked for specific leagues. If we can't filter by league easily, 
    # we might just let all cricket through or filter by team. 
    # Let's let all Cricket through if it matches the league list logic, 
    # but since API structure varies, we'll rely on the manual lists if possible.
    if g['sport'] == "Cricket":
         # Basic check for now:
         if any(l in g.get('league', '') for l in CRICKET_LEAGUES):
             return True

    return False

def fetch_real_news():
    """Fetches the top general sports headline from ESPN"""
    try:
        # Fetching Top Headlines
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news" # NBA usually has good general headlines, or use 'general'
        data = requests.get(url).json()
        article = data['articles'][0]
        return {
            "headline": article['headline'],
            "description": article['description'],
            "story": article.get('story', article['description']) # sometimes 'story' is not full
        }
    except:
        return {
            "headline": "Sports World Updates",
            "description": "Live updates from around the globe.",
            "story": "Check back later for detailed reports."
        }

def main():
    if not SCORES_PATH.exists():
        print("No scores found.")
        return

    with open(SCORES_PATH) as f:
        raw_data = json.load(f)

    # 1. Filter Games
    relevant_games = [g for g in raw_data.get("games", []) if game_is_relevant(g)]

    # 2. Get News
    news = fetch_real_news()

    # 3. Create Final Output
    output = {
        "updated": datetime.utcnow().isoformat(),
        "games": relevant_games, # Only save the filtered ones for the frontend
        "lead_headline": news['headline'],
        "preview_story": news['description'],
        "detailed_story": news['story']
    }

    # Save over the daily_scores (or a new file if you prefer)
    # The frontend reads daily_scores for games, so we should update that file 
    # OR we update the 'stories' file and let frontend read both.
    
    # We will save the FILTERED games back to daily_scores so the ticker is clean
    with open(SCORES_PATH, "w") as f:
        json.dump({"updated": output["updated"], "games": relevant_games}, f, indent=2)

    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Filtered down to {len(relevant_games)} relevant games.")

if __name__ == "__main__":
    main()
