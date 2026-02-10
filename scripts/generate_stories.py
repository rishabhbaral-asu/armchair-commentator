import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- PINNED CONTENT ---
PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13 to claim title",
        "dateline": "SANTA CLARA, Calif.", 
        "body": "The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that stifled one of the league's most potent offenses, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks and forcing three turnovers.\n\nSam Darnold was efficient, throwing for 215 yards and two touchdowns, finding a rhythm early that the Patriots could not match. Kenneth Walker III added 112 yards on the ground, controlling the clock and the tempo.",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Super Bowl MVP", "headers": ["Player", "Stat", "Desc"], "rows": [["S. Darnold", "22/28", "2 TD"], ["K. Walker", "112", "Yards"]] }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "65°F", "desc": "Clear skies.", "high": "72", "low": "48"},
    "quote": {"text": "Tonight, the only ghost out there was the history we just buried.", "author": "Sam Darnold"},
    "staff": ["Editor: R. Baral", "Data: ESPN API"],
    "date": datetime.now().strftime("%A, %B %d, %Y")
}

# --- NARRATIVE ANALYSIS ENGINE ---

def analyze_matchup(game):
    """
    Determines the narrative archetype based on records and ranks.
    Returns: (Archetype String, Context Sentence)
    """
    h_rec = game.get('home_record', '')
    a_rec = game.get('away_record', '')
    h_rank = game.get('home_rank')
    a_rank = game.get('away_rank')
    
    # 1. CLASH OF TITANS (Both Ranked)
    if h_rank and a_rank:
        return "TITANS", f"A heavyweight bout is set for {game['venue']} as No. {a_rank} {game['away']} visits No. {h_rank} {game['home']}."
    
    # 2. UPSET ALERT (Unranked Home vs Ranked Away)
    if a_rank and not h_rank:
        return "UPSET_WATCH", f"The {game['home']} have a chance to shake up the rankings when they host the No. {a_rank} {game['away']}."
    
    # 3. ANALYZE RECORDS (If parsable)
    # Simple logic: check if one team has way more wins
    try:
        # Assuming record format "W-L" or "W-L-T"
        def get_wins(rec): return int(rec.split('-')[0]) if '-' in rec else 0
        h_wins = get_wins(h_rec)
        a_wins = get_wins(a_rec)
        
        if h_wins > a_wins + 5:
            return "MISMATCH", f"The {game['home']} ({h_rec}) look to continue their dominant run against the struggling {game['away']} ({a_rec})."
        elif a_wins > h_wins + 5:
            return "ROAD_WARRIOR", f"The {game['away']} ({a_rec}) arrive at {game['venue']} looking to spoil the party for the {game['home']} ({h_rec})."
        elif h_wins > 0 and a_wins > 0: # Avoid 0-0 early season
             return "EVEN_MATCH", f"Separated by a razor-thin margin in the standings, the {game['home']} ({h_rec}) and {game['away']} ({a_rec}) clash with critical momentum on the line."
    except:
        pass

    # Default
    return "STANDARD", f"The {game['home']} ({h_rec}) take on the {game['away']} ({a_rec}) in a matchup pivotal for both sides."

# --- GENERATION ---

def generate_headline(game, margin, state):
    h_rank = game.get('home_rank')
    a_rank = game.get('away_rank')
    
    prefix_h = f"#{h_rank} " if h_rank else ""
    prefix_a = f"#{a_rank} " if a_rank else ""

    if state == 'pre':
        if game.get('headline'): return game['headline']
        return f"{prefix_a}{game['away']} at {prefix_h}{game['home']}"
    
    if "CRICKET" in game['sport']:
        return f"{game['away']} vs {game['home']}"
        
    if state == 'post':
        winner = game['home'] if margin > 0 else game['away']
        return f"{winner} Wins"
        
    return "Live Action"

def generate_dynamic_narrative(game):
    # CRICKET BYPASS
    if "CRICKET" in game['sport'].upper():
        return f"CRICKET MATCH: {game['away']} vs {game['home']}. Status: {game['status']}."

    home = game.get('home')
    away = game.get('away')
    venue = game.get('venue')
    status = game.get('status', '')
    state = game.get('state', '')
    leaders = game.get('leaders', [])
    headline = game.get('headline', '')
    odds = game.get('odds', '')
    
    archetype, context_lede = analyze_matchup(game)
    
    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        margin = 0
        h_s = game.get('home_score', '0')
        a_s = game.get('away_score', '0')

    # A. PREVIEW (The "Expert" Analysis)
    if state == 'pre':
        # 1. The Context Lede (Generated above)
        lede = context_lede
        
        # 2. The Headline Integration
        if headline:
            lede += f" The storyline dominating the pre-game chatter: {headline}."

        # 3. The Stakes (Odds & Rankings)
        stakes = ""
        if odds:
            stakes = f" Vegas has set the line at {odds}, predicting a tight contest."
            
        # 4. Player Watch
        player = ""
        if leaders:
            l = leaders[0]
            player = f" \n\nKey Matchup: All eyes will be on {l['name']}. Coming off a performance of {l['stat']} {l['desc']}, {l['name']} will need to be contained if the opposition hopes to secure a result."

        # 5. Closer
        closer = f"\n\nGame time is set for {status}."

        return f"{lede}{stakes}{player}{closer}"

    # B. LIVE (The Update)
    if state == 'in':
        leader = home if margin > 0 else away
        return (
            f"LIVE: It's {leader} with the advantage at {venue}, leading {h_s}-{a_s}. "
            f"We are currently in the {status}. {leader} is looking to maintain their momentum against a resilient opposition."
        )

    # C. FINAL (The Recap)
    if state == 'post':
        winner = home if margin > 0 else away
        loser = away if margin > 0 else home
        
        stat_txt = ""
        if leaders:
            l = leaders[0]
            stat_txt = f" {l['name']} led the way with {l['stat']} {l['desc']}."
            
        return (
            f"FINAL: The {winner} defeated the {loser} {h_s}-{a_s} at {venue}. "
            f"{winner} executed down the stretch to seal the win.{stat_txt} "
            f"This result could have significant implications for the standings moving forward."
        )

    return "Updates to follow."

def generate_grid_item(game):
    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        margin = 0

    return {
        "id": f"game-{game.get('game_id')}",
        "type": "grid",
        "sport": game['sport'],
        "headline": generate_headline(game, margin, game['state']),
        "subhead": game['status'],
        "dateline": game['venue'],
        "body": generate_dynamic_narrative(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            for g in raw_data.get("games", []):
                if g['home'] != "Seahawks" and g['away'] != "Seahawks":
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} Press-Ready Stories.")

if __name__ == "__main__":
    main()
