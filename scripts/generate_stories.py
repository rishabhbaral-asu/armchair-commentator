import json
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. PAST STORIES (Formatted EXACTLY like AP Reports) ---

# Super Bowl Recap
SB_BODY = """LAS VEGAS -- The Seattle Seahawks (14-6) vs. The New England Patriots (13-7)
Santa Clara, Calif.; Sunday, 4:30 p.m. MST

BOTTOM LINE: Defense rules the day as Seattle claims its second Lombardi Trophy.

The Seahawks culminated a miraculous postseason run by dismantling the Patriots 29-13 in Super Bowl LX. Seattle's defense, led by head coach Mike Macdonald, recorded seven sacks and forced three turnovers, holding the high-powered New England offense to season lows in total yards (240) and points (13).

The Patriots entered the game averaging 28.4 points per contest but were stifled by Seattle's simulated pressures. Drake Maye, the NFL MVP runner-up, was harassed constantly, finishing 18-of-41 passing.

Seattle's offense was efficient. Sam Darnold threw for 215 yards and two scores, while Kenneth Walker III rushed for 112 yards and a touchdown.

TOP PERFORMERS: Sam Darnold completed 22 of 28 passes for 215 yards and 2 TDs. Kenneth Walker III averaged 5.1 yards per carry. 
For New England, Ja'Lynn Polk caught 6 passes for 84 yards.

INJURIES: Seahawks: Abraham Lucas: active (knee). Patriots: Cole Strange: out (knee)."""

# Cricket Recap (India vs USA)
CRICKET_BODY = """MUMBAI -- India (1-0) vs. United States (0-1)
Wankhede Stadium, Mumbai; Sunday

BOTTOM LINE: Suryakumar Yadav's captain's knock saves India from a historic upset against USA.

India defeated the United States by 7 wickets in their T20 World Cup opener. Chasing a modest target, India collapsed to 34/4 inside the powerplay before Yadav (84*) anchored the innings. 

The United States, playing in their first World Cup on Indian soil, utilized the swinging conditions effectively early. Saurabh Netravalkar claimed two early wickets. However, the depth of the Indian batting lineup proved the difference.

TOP PERFORMERS: Suryakumar Yadav scored 84 not out off 48 balls. Arshdeep Singh took 4 wickets for 18 runs for India.
For USA, Steven Taylor scored 42 off 35 balls.

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

# --- 2. AP STYLE GENERATOR (For Live Games) ---

def generate_ap_story(game):
    # Data extraction
    home = game['home']
    away = game['away']
    h_rec = game.get('home_record', '')
    a_rec = game.get('away_record', '')
    venue = game.get('venue', '')
    location = game.get('location', venue)
    time = game.get('status', '')
    odds = game.get('odds', '')
    
    # 1. HEADER
    header = f"{away} ({a_rec}) vs. {home} ({h_rec})\n{location}; {time}"
    
    # 2. BOTTOM LINE
    bottom_line = ""
    if game['state'] == 'pre':
        if odds:
            bottom_line = f"BOTTOM LINE: The {home} look to cover the {odds} spread against the {away}."
        else:
            bottom_line = f"BOTTOM LINE: The {home} host the {away} in a {game['league']} matchup."
    elif game['state'] == 'in':
         bottom_line = f"BOTTOM LINE: The {home} and {away} are currently meeting in {location}."
    else: # Final
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        winner = home if h_s > a_s else away
        loser = away if winner == home else home
        bottom_line = f"BOTTOM LINE: The {winner} defeated the {loser} {h_s}-{a_s}."

    # 3. STAT BLOCK (Generic Text generation based on sport)
    stats_block = ""
    if "BASKETBALL" in game['sport']:
        stats_block = (
            f"The {home} are averaging points on offense this season, while allowing opponents to score. "
            f"The {away} enter the game allowing points per game. "
            f"This is the first meeting of the season between the two teams."
        )
    elif "CRICKET" in game['sport']:
        stats_block = (
            f"The match features two sides looking to improve their standing in the table. "
            f"Conditions at {venue} are expected to favor the batsmen early."
        )
    else:
        stats_block = f"The {home} ({h_rec}) face the {away} ({a_rec})."

    # 4. TOP PERFORMERS
    performers = "TOP PERFORMERS: "
    leaders = game.get('leaders', [])
    if leaders:
        p_list = []
        for l in leaders:
            p_list.append(f"{l['name']} ({l['team']}) is recording {l['stat']} ({l['desc']}).")
        performers += " ".join(p_list)
    else:
        performers += "Stats not yet available."

    # 5. INJURIES (Placeholder as scraping injury lists is complex)
    injuries = "INJURIES: Updates to be provided."

    return f"{header}\n\n{bottom_line}\n\n{stats_block}\n\n{performers}\n\n{injuries}"


def generate_grid_item(game):
    return {
        "id": f"game-{game.get('game_id')}",
        "type": "grid",
        "sport": game['sport'],
        "headline": f"{game['away']} vs {game['home']}",
        "subhead": game['status'],
        "dateline": game['location'],
        "body": generate_ap_story(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            for g in raw_data.get("games", []):
                if g['home'] != "Seahawks": # No dupes
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} AP-Style Stories.")

if __name__ == "__main__":
    main()
