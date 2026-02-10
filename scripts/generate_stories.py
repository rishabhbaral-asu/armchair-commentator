import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. PINNED STORIES (Rewritten in the "New Style") ---

# Super Bowl Recap - The "Gold Standard" Example
SB_BODY = """SANTA CLARA, Calif. — Seattle Seahawks (14-6) vs. New England Patriots (13-7)
Levi's Stadium; Sunday

BOTTOM LINE: The "Legion of Boom" returns in spirit as Seattle suffocates the Patriots dynasty.

The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that stifled one of the league's most potent offenses, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks and forcing three turnovers.

"Nobody talked about our front seven," Macdonald said postgame. "I think they're talking now."

The Patriots entered the game averaging 28.4 points per contest but were held to season lows in total yards (240) and points (13). Seattle's simulated pressures confused the sophomore quarterback all night.

Offensively, Sam Darnold exorcised the ghosts of his past. The veteran signal-caller was surgical, completing 22-of-28 passes for 215 yards and two touchdowns, finding a rhythm early that New England could not disrupt.

TOP PERFORMERS: Kenneth Walker III (SEA) pounded the rock for 112 yards and a touchdown. Sam Darnold (SEA) finished with a 115.4 passer rating. Ja'Lynn Polk (NE) provided the lone spark for New England with 6 catches for 84 yards.

INJURIES: Cole Strange (NE) left in the 2nd Quarter (knee)."""

# Cricket Recap - The "Global Wire" Example
CRICKET_BODY = """MUMBAI — India (1-0) vs. United States (0-1)
Wankhede Stadium; Sunday

BOTTOM LINE: Suryakumar Yadav rescues India from a historic upset against the USA.

The cricketing world nearly witnessed the upset of the century. Chasing a modest target of 133, the powerhouse Indian lineup crumbled to 34/4 inside the powerplay, silenced by a spirited American bowling attack utilizing the swinging conditions at Wankhede.

Enter Suryakumar Yadav. The captain played a knock for the ages, abandoning his usual flamboyant style for a gritty, unbeaten 84 off 48 balls. He anchored partnerships with the lower order, slowly shifting the momentum back to the hosts before exploding in the final overs to secure victory by 7 wickets.

"We knew the new ball would do a bit," Yadav admitted. "But credit to the USA, they put us under immense pressure."

TOP PERFORMERS: Suryakumar Yadav (IND) scored 84* (48). Arshdeep Singh (IND) tore through the USA top order with 4/18. Steven Taylor (USA) top-scored for the visitors with a counter-attacking 42.

INJURIES: None reported."""

PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "Seahawks 29, Patriots 13", 
        "subhead": "Seattle defense dominates New England to win Super Bowl LX",
        "dateline": "SANTA CLARA, Calif.", "body": SB_BODY,
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Leaders", "headers": ["Player", "Stat"], "rows": [["S. Darnold", "215 Yds, 2 TD"], ["K. Walker", "112 Rush Yds"]] }
    },
    {
        "id": "cricket-ind-usa", "type": "sidebar", "sport": "CRICKET • T20 WC",
        "headline": "India def. USA (7 wkts)",
        "subhead": "Yadav (84*) rescues hosts after early collapse",
        "dateline": "MUMBAI", "body": CRICKET_BODY,
        "game_data": { "home": "India", "home_score": "161/3", "home_logo": "https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg", "away": "USA", "away_score": "132/8", "away_logo": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Flag_of_the_United_States.svg", "status": "FINAL" },
        "box_score": None
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "72°F", "desc": "Sunny", "high": "75", "low": "50"},
    "quote": {"text": "Nobody talked about our front seven. I think they're talking now.", "author": "Mike Macdonald"},
    "staff": ["Associated Press", "Data Skrive"],
    "date": datetime.now().strftime("%A, %B %d, %Y")
}

# --- 2. THE WRITER ENGINE (Context + Personality) ---

def analyze_matchup(game):
    h_rec = game.get('home_record', '')
    a_rec = game.get('away_record', '')
    h_rank = game.get('home_rank')
    a_rank = game.get('away_rank')
    
    # Context Logic
    if h_rank and a_rank:
        return f"A heavyweight clash with significant playoff implications features No. {a_rank} {game['away']} visiting No. {h_rank} {game['home']}."
    elif a_rank and not h_rank:
        return f"The {game['home']} ({h_rec}) have a prime opportunity to shake up the rankings as they host the No. {a_rank} {game['away']}."
    else:
        return f"Two squads looking to establish momentum collide as the {game['away']} ({a_rec}) visit the {game['home']} ({h_rec})."

def generate_live_story(game):
    # Data extraction
    home = game['home']
    away = game['away']
    h_rec = game.get('home_record', '')
    a_rec = game.get('away_record', '')
    venue = game.get('venue', 'Neutral Site')
    location = game.get('location', venue)
    status = game.get('status', '')
    odds = game.get('odds', '')
    headline = game.get('headline', '')
    
    # 1. HEADER BLOCK
    header = f"{location.upper()} — {away} ({a_rec}) vs. {home} ({h_rec})\n{venue}; {status}"
    
    # 2. BOTTOM LINE (The Hook)
    bottom_line = ""
    if game['state'] == 'pre':
        if odds:
            bottom_line = f"BOTTOM LINE: The {home} look to cover the {odds} spread in a pivotal matchup."
        elif headline:
            bottom_line = f"BOTTOM LINE: {headline}"
        else:
            bottom_line = f"BOTTOM LINE: The {home} host the {away} looking to improve their standing."
    elif game['state'] == 'in':
         bottom_line = f"BOTTOM LINE: Live action from {location} as {home} and {away} trade blows."
    else:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        winner = home if h_s > a_s else away
        bottom_line = f"BOTTOM LINE: The {winner} make a statement with a {h_s}-{a_s} victory."

    # 3. NARRATIVE BODY (Humanized)
    context = analyze_matchup(game)
    
    body_text = ""
    if "CRICKET" in game['sport']:
        body_text = (
            f"{context} Conditions at {venue} are expected to play a major role. "
            f"The {home} will look to capitalize on their familiarity with the surface, while {away} hope to silence the home crowd early."
        )
    elif "BASKETBALL" in game['sport']:
        body_text = (
            f"{context} The {home} have relied on a high-octane offense this season, but they face a stern test against the disciplined defense of the {away}. "
            f"Execution in the half-court will likely determine the winner of this contest."
        )
    else:
        body_text = (
            f"{context} "
            f"The {home} are looking to defend their home turf, while the {away} aim to play spoiler on the road."
        )

    # 4. TOP PERFORMERS (Data Injection)
    performers = "TOP PERFORMERS: "
    leaders = game.get('leaders', [])
    if leaders:
        p_list = []
        for l in leaders:
            # "J. Smith (SEA) is averaging 25.0 PPG."
            p_list.append(f"{l['name']} ({l['team']}) is pacing the squad with {l['stat']} ({l['desc']}).")
        performers += " ".join(p_list)
    else:
        performers += "Stats will be updated as action unfolds."

    # 5. INJURIES (The Footer)
    injuries = "INJURIES: Updates to be provided."

    return f"{header}\n\n{bottom_line}\n\n{body_text}\n\n{performers}\n\n{injuries}"


def generate_grid_item(game):
    return {
        "id": f"game-{game.get('game_id')}",
        "type": "grid",
        "sport": game['sport'],
        "headline": f"{game['away']} vs {game['home']}",
        "subhead": game['status'],
        "dateline": game['location'],
        "body": generate_live_story(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            for g in raw_data.get("games", []):
                # Dedupe
                if g['home'] != "Seahawks": 
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} High-Fidelity Stories.")

if __name__ == "__main__":
    main()
