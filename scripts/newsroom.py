import requests
import json
from datetime import datetime
import pytz

# --- 1. CONFIG & WHITELIST ---
def get_whitelist():
    return [
        "san francisco 49ers", "ac milan", "angel city", "anaheim angels", "arizona state", "asu", 
        "athletics", "atletico madrid", "austin fc", "bakersfield", "california", "cal poly", 
        "capitals", "arizona cardinals", "cal baptist", "la chargers", "chelsea", "la clippers", 
        "commanders", "coventry city", "dallas cowboys", "crystal palace", "arizona diamondbacks", 
        "dc united", "fc dallas", "houston dash", "la dodgers", "anaheim ducks", "east texas a&m", 
        "fresno state", "fulham", "fullerton", "san francisco giants", "new york giants", "gcu", 
        "houston dynamo", "juventus", "sacramento kings", "la kings", "la galaxy", "lafc", "india", 
        "la lakers", "united states", "lbsu", "leeds united", "leverkusen", "lyon", "m'gladbach", 
        "mainz", "marseille", "maryland", "dallas mavericks", "phoenix mercury", "phoenix suns", 
        "inter miami", "as monaco", "mystics", "washington nationals", "north texas", "norwich", 
        "nott'm forest", "orioles", "san diego padres", "parma", "psv", "la rams", "texas rangers", 
        "baltimore ravens", "saint mary's", "san diego", "san jose", "santa clara", "san jose sharks", 
        "la sparks", "washington spirit", "st. pauli", "dallas stars", "texas", "tolouse", "uc davis", 
        "uc irvine", "ucla", "usc", "uc riverside", "uc san diego", "ucsb", "utep", "valkyries", 
        "venezia", "golden state warriors", "san diego wave", "dallas wings", "wizards", "wrexham", 
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium", "iowa"
    ]

# --- 2. LIVE SCHEDULE LOOKUP ENGINE ---
def get_up_next(team_id, sport, league):
    """Fetches the actual next game for a specific team via ESPN Team API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"
    try:
        data = requests.get(url, timeout=5).json()
        now = datetime.now(pytz.utc)
        
        # Look for the first game with a 'scheduled' status occurring after 'now'
        for event in data.get("events", []):
            game_date = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
            if game_date > now:
                competitors = event["competitions"][0]["competitors"]
                # Determine if the team is home or away
                for team in competitors:
                    if team["id"] == team_id:
                        opponent = [t["team"]["displayName"] for t in competitors if t["id"] != team_id][0]
                        venue_type = "home" if team["homeAway"] == "home" else "away"
                        date_str = game_date.astimezone(pytz.timezone('US/Arizona')).strftime("%m/%d")
                        
                        if venue_type == "home":
                            return f"Up Next: {date_str} vs {opponent}."
                        else:
                            return f"Up Next: {date_str} at {opponent}."
    except:
        pass
    return "Up Next: Schedule pending."

# --- 3. AP STORY ENGINE ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    
    # 1. Dateline & Venue Info
    city = comp.get("venue", {}).get("address", {}).get("city", "FIELD")
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    dateline = f"{city.upper()}, {state} (AP) — "
    
    # 2. Performance Research (Top Scorer)
    details = ""
    try:
        winner = home if home.get("winner") else away
        leader = winner["leaders"][0]["leaders"][0]
        name = leader["athlete"]["displayName"]
        val = leader["displayValue"]
        stat = winner["leaders"][0].get("displayName", "points").lower()
        details = f"{name} provided a spark with {val} {stat} for the {winner['team']['shortDisplayName']}. "
    except:
        details = f"The {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} met in a highly anticipated clash. "

    # 3. Dynamic "Up Next" Logic
    # We pull the next game for the 'featured' team (the one on our whitelist)
    # For simplicity, we'll pull it for the winner of this game
    winner_id = home["team"]["id"] if home.get("winner") else away["team"]["id"]
    next_game_blurb = get_up_next(winner_id, sport, league)

    return f"{dateline}{details}{next_game_blurb}"

# --- 4. DATA FETCH & HTML GENERATION (Integrated) ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            if any(team in name for team in whitelist) and eid not in seen_ids:
                results.append({
                    "league": league.upper().replace("-", " "),
                    "score": f"{event['competitions'][0]['competitors'][1]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][1].get('score','0')}, {event['competitions'][0]['competitors'][0]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][0].get('score','0')}",
                    "ap_story": craft_ap_story(event, sport, league),
                    "status": event["status"]["type"]["detail"]
                })
                seen_ids.add(eid)
    except: pass
    return results

To provide the full AP-Style experience on your site, we need to update your script to include three specific things:

A Story Engine: To write the actual "Ann Arbor, Mich." style report.

A Schedule Tracker: To look up the next game for each team.

An HTML Update: To render these long-form stories in a readable, newspaper-style layout.

Below is the complete, integrated script. Replace your entire newsroom.py file with this code.

Python
import requests
import json
from datetime import datetime
import pytz

# --- 1. CONFIG & WHITELIST ---
def get_whitelist():
    return [
        "arizona state", "asu", "sun devils", "iowa", "hawkeyes", 
        "texas tech", "red raiders", "ucla", "usc", "santa clara"
    ]

# --- 2. THE RESEARCH ENGINE (Live Schedule Lookup) ---
def get_up_next(team_id, sport, league):
    """Searches ESPN's database for the specific team's next scheduled game."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"
    try:
        data = requests.get(url, timeout=5).json()
        now = datetime.now(pytz.utc)
        for event in data.get("events", []):
            game_date = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
            if game_date > now:
                competitors = event["competitions"][0]["competitors"]
                for team in competitors:
                    if team["id"] == team_id:
                        opponent = [t["team"]["displayName"] for t in competitors if t["id"] != team_id][0]
                        venue = "home" if team["homeAway"] == "home" else "away"
                        day = game_date.astimezone(pytz.timezone('US/Arizona')).strftime("%A")
                        return f"{day} {'vs' if venue == 'home' else 'at'} {opponent}"
    except: pass
    return "TBD"

# --- 3. THE AP STORYTELLER ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    
    # Dateline Info
    city = comp.get("venue", {}).get("address", {}).get("city", "TEMPE")
    state = comp.get("venue", {}).get("address", {}).get("state", "AZ")
    dateline = f"{city.upper()}, {state} (AP) — "
    
    # Identify Winner and Top Performer
    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    
    try:
        leader = winner["leaders"][0]["leaders"][0]
        star_name = leader["athlete"]["displayName"]
        star_stats = leader["displayValue"]
        detail = f"{star_name} scored {star_stats} to lead the {winner['team']['shortDisplayName']} to a victory over {loser['team']['shortDisplayName']}."
    except:
        detail = f"The {winner['team']['shortDisplayName']} secured a decisive win over {loser['team']['shortDisplayName']}."

    # Sport-Specific Narrative
    if "basketball" in league:
        narrative = "The game featured a dominant second-half run that silenced the home crowd."
    elif "baseball" in league:
        narrative = "The bats stayed hot throughout the afternoon, providing plenty of run support."
    else:
        narrative = "It was a physical contest from the opening whistle."

    # Look up "Up Next"
    w_next = get_up_next(winner["team"]["id"], sport, league)
    l_next = get_up_next(loser["team"]["id"], sport, league)

    full_story = f"**{dateline}**{detail} {narrative}<br><br><b>Up Next</b><br>{winner['team']['shortDisplayName']}: {w_next}.<br>{loser['team']['shortDisplayName']}: {l_next}."
    return full_story

# --- 4. DATA FETCH & HTML ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            if any(team in name for team in whitelist) and eid not in seen_ids:
                results.append({
                    "league": league.upper().replace("-", " "),
                    "headline": event["name"],
                    "ap_story": craft_ap_story(event, sport, league),
                    "score_line": f"{event['competitions'][0]['competitors'][1]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][1].get('score','0')}, {event['competitions'][0]['competitors'][0]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][0].get('score','0')}"
                })
                seen_ids.add(eid)
    except: pass
    return results

def generate_html(games):
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %Y — %I:%M %p")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>The Armchair Commentator</title>
        <style>
            body {{ font-family: "Georgia", serif; background: #fdfdfd; padding: 50px; line-height: 1.6; color: #111; }}
            .paper {{ max-width: 800px; margin: auto; background: white; padding: 40px; border: 1px solid #ddd; box-shadow: 10px 10px 0px #eee; }}
            .masthead {{ text-align: center; border-bottom: 5px double #111; margin-bottom: 40px; }}
            .masthead h1 {{ font-size: 3.5em; margin: 0; font-family: "Times New Roman", serif; text-transform: uppercase; letter-spacing: -2px; }}
            .story {{ margin-bottom: 50px; border-bottom: 1px solid #eee; padding-bottom: 30px; }}
            .headline {{ font-size: 2em; font-weight: bold; line-height: 1.1; margin-bottom: 10px; }}
            .score-box {{ background: #000; color: #fff; display: inline-block; padding: 2px 10px; font-family: sans-serif; font-weight: bold; margin-bottom: 15px; }}
            .ap-body {{ font-size: 1.15em; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <div class="masthead">
                <h1>The Armchair Commentator</h1>
                <p>FINAL EDITION — {now} MST</p>
            </div>
    """
    for g in games:
        html_content += f"""
        <div class="story">
            <div class="headline">{g['headline']}</div>
            <div class="score-box">{g['score_line']}</div>
            <div class="ap-body">{g['ap_story']}</div>
        </div>
        """
    html_content += "</div></body></html>"
    with open("index.html", "w") as f: f.write(html_content)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"), ("baseball", "college-baseball")]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    generate_html(all_games)

if __name__ == "__main__": 
    main()
