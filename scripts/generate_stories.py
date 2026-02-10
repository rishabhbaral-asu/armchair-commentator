import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- PINNED CONTENT (Unchanged) ---
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

# --- SPORT CONTEXT ENGINE ---
SPORT_TERMS = {
    "basketball": {"start": "tip-off", "venue_action": "take the floor at", "unit": "points"},
    "football": {"start": "kickoff", "venue_action": "collide at", "unit": "points"},
    "soccer": {"start": "kickoff", "venue_action": "meet at", "unit": "goals"},
    "baseball": {"start": "first pitch", "venue_action": "take the field at", "unit": "runs"},
    "hockey": {"start": "puck drop", "venue_action": "face off at", "unit": "goals"},
}

def get_sport_context(sport_name):
    for key, context in SPORT_TERMS.items():
        if key in sport_name.lower(): return context
    return {"start": "start", "venue_action": "meet at", "unit": "points"}

# --- CRICKET SPECIALIST ---
def generate_cricket_narrative(game):
    """
    Handles complex string scores like '161/5 (20)' vs '150/9 (20)'
    """
    home = game['home']
    away = game['away']
    venue = game.get('venue', 'the ground')
    status = game.get('status', '')
    state = game.get('state', '')
    leaders = game.get('leaders', [])
    h_sc = game.get('home_score', '0')
    a_sc = game.get('away_score', '0')
    
    # Pre-Game
    if state == 'pre':
        return (
            f"PREVIEW: The cricketing world turns its eyes to {venue} as {home} face {away}. "
            f"Both sides are looking to establish dominance in the format. "
            f"The toss will be crucial in determining the flow of the match. Play is scheduled to begin at {status}."
        )

    # In-Play / Post-Game Parsing
    # Attempt to extract runs for basic margin calc
    try:
        h_runs = int(h_sc.split('/')[0]) if '/' in h_sc else int(h_sc.split(' ')[0])
        a_runs = int(a_sc.split('/')[0]) if '/' in a_sc else int(a_sc.split(' ')[0])
        diff = h_runs - a_runs
    except:
        h_runs, a_runs, diff = 0, 0, 0

    if state == 'in':
        return (
            f"LIVE: Action is underway at {venue}. {home} have posted {h_sc}, while {away} are currently {a_sc}. "
            f"The match is finely poised in the {status}. Key partnerships will define the next phase of play."
        )

    if state == 'post':
        winner = home if diff > 0 else away
        loser = away if diff > 0 else home
        
        stat_line = ""
        if leaders:
            l = leaders[0]
            stat_line = f" The victory was anchored by {l['name']}, who contributed {l['stat']} ({l['desc']})."
            
        return (
            f"FINAL: {winner} defeated {loser} at {venue}. "
            f"Final scores: {home} {h_sc}, {away} {a_sc}.{stat_line} "
            f"A solid performance in the field secured the result."
        )

    return f"{home} vs {away} at {venue}."

# --- STANDARD NARRATIVE ENGINE ---
def generate_dynamic_narrative(game):
    if "CRICKET" in game['sport'].upper():
        return generate_cricket_narrative(game)

    home = game.get('home')
    away = game.get('away')
    venue = game.get('venue', 'the arena')
    status = game.get('status', '')
    state = game.get('state', '')
    leaders = game.get('leaders', [])
    headline = game.get('headline', '')
    odds = game.get('odds', '')
    h_rec = game.get('home_record', '')
    a_rec = game.get('away_record', '')
    
    ctx = get_sport_context(game['sport'])

    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        margin = 0
        h_s = game.get('home_score', '0')
        a_s = game.get('away_score', '0')

    # A. PREVIEW
    if state == 'pre':
        # 1. The Hook
        hook = f"The {home} ({h_rec}) play host to the {away} ({a_rec})"
        if headline: hook = f"{headline}. That's the storyline as the {home} ({h_rec}) host the {away} ({a_rec})"
        
        # 2. The Stakes (Odds)
        stakes = ""
        if odds:
            stakes = f" The oddsmakers have set the line at {odds}, expecting a competitive affair."
            
        # 3. Player Watch
        player = ""
        if leaders:
            l = leaders[0]
            player = f" All eyes will be on {l['name']}, coming off a performance of {l['stat']} {l['desc']}."

        return (
            f"PREVIEW: {hook} at {venue}. The teams {ctx['venue_action']} {venue} looking to improve their standing.{stakes}"
            f"{player} {ctx['start'].capitalize()} is set for {status}."
        )

    # B. LIVE
    if state == 'in':
        leader = home if margin > 0 else away
        return (
            f"LIVE: It's {leader} with the advantage at {venue}, leading {h_s}-{a_s}. "
            f"We are currently in the {status}. {leader} is looking to maintain their momentum against a resilient opposition."
        )

    # C. FINAL
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
            f"With the win, {winner} moves to {h_rec if winner == home else a_rec}."
        )

    return "Updates to follow."

def generate_headline(game, margin, state):
    if state == 'pre':
        if game.get('headline'): return game['headline']
        return f"{game['away']} @ {game['home']}"
    
    if "CRICKET" in game['sport']:
        return f"{game['away']} vs {game['home']}"
        
    if state == 'post':
        winner = game['home'] if margin > 0 else game['away']
        return f"{winner} Wins"
        
    return "Live Action"

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

    print(f"Generated {len(final_stories)} ESPN-Style Stories (Cricket Enabled).")

if __name__ == "__main__":
    main()
