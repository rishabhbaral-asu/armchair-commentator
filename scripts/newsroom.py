import requests
import json
from datetime import datetime
import pytz

# --- 1. CONFIG & WHITELIST ---
def get_whitelist():
    """Returns the list of teams to monitor."""
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

# --- 2. LIVE SCHEDULE RESEARCH ---
def get_up_next(team_id, sport, league):
    """Fetches the actual next game for a team via ESPN Team API."""
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
                        opp = [t["team"]["displayName"] for t in competitors if t["id"] != team_id][0]
                        venue = "home" if team["homeAway"] == "home" else "away"
                        # Format date for Arizona time
                        date_str = game_date.astimezone(pytz.timezone('US/Arizona')).strftime("%m/%d")
                        return f"{date_str} {'vs' if venue == 'home' else 'at'} {opp}"
    except: pass
    return "TBD"

# --- 3. AP STORY ENGINE ---
def craft_ap_story(event, sport, league):
    """Generates a realistic AP-style news report."""
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "FIELD")
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    dateline = f"**{city.upper()}, {state} (AP) — **"
    
    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    
    # Research top performer
    try:
        leader = winner["leaders"][0]["leaders"][0]
        name = leader["athlete"]["displayName"]
        val = leader["displayValue"]
        stat = winner["leaders"][0].get("displayName", "points").lower()
        detail = f"{name} led the way with {val} {stat} as the {winner['team']['shortDisplayName']} handled {loser['team']['shortDisplayName']}."
    except:
        detail = f"The {winner['team']['shortDisplayName']} utilized a balanced attack to secure the win over {loser['team']['shortDisplayName']}."

    # Fetch next game schedule
    w_next = get_up_next(winner["team"]["id"], sport, league)
    
    return f"{dateline}{detail}<br><br><b>Up Next:</b> {winner['team']['shortDisplayName']} ({w_next})."

# --- 4. DATA FETCH (Logos & Scores) ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            if any(team in name for team in whitelist) and eid not in seen_ids:
                comp = event["competitions"][0]
                results.append({
                    "headline": event.get("name", "Game Update"),
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "score_line": f"{comp['competitors'][1]['team']['shortDisplayName']} {comp['competitors'][1].get('score','0')}, {comp['competitors'][0]['team']['shortDisplayName']} {comp['competitors'][0].get('score','0')}",
                    "ap_story": craft_ap_story(event, sport, league),
                    "status": event["status"]["type"]["detail"]
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 5. GRAPHIC HTML GENERATOR ---
def generate_html(games):
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %Y")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 40px; color: #1c1e21; }}
            .container {{ max-width: 850px; margin: auto; }}
            .header {{ text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #ddd; }}
            .header h1 {{ font-family: 'Times New Roman', serif; font-size: 3.5em; margin: 0; text-transform: uppercase; }}
            .card {{ background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; border: 1px solid #ddd; }}
            .card-header {{ background: #24292e; color: white; padding: 12px 20px; font-weight: bold; display: flex; justify-content: space-between; }}
            .score-strip {{ display: flex; align-items: center; justify-content: space-around; padding: 25px; background: #fafbfc; border-bottom: 1px solid #eee; }}
            .team-img {{ height: 70px; width: 70px; object-fit: contain; }}
            .score-text {{ font-size: 2.2em; font-weight: 800; letter-spacing: -1px; }}
            .story-body {{ padding: 25px; font-size: 1.15em; line-height: 1.6; }}
            .up-next-box {{ background: #fff8e1; padding: 10px 15px; border-radius: 4px; border-left: 4px solid #ffc107; font-size: 0.9em; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>The Armchair Commentator</h1>
                <p>{now} | Sports Desk Edition</p>
            </div>
    """
    if not games:
        html_content += '<p style="text-align:center; color:#888;">No games found for your whitelist teams today.</p>'
    else:
        for g in games:
            html_content += f"""
            <div class="card">
                <div class="card-header">
                    <span>{g['headline']}</span>
                    <span>{g['status']}</span>
                </div>
                <div class="score-strip">
                    <img src="{g['away_logo']}" class="team-img">
                    <div class="score-text">{g['score_line']}</div>
                    <img src="{g['home_logo']}" class="team-img">
                </div>
                <div class="story-body">
                    {g['ap_story']}
                </div>
            </div>
            """
    html_content += "</div></body></html>"
    with open("index.html", "w") as f: 
        f.write(html_content)

# --- 6. MAIN EXECUTION ---
def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("basketball", "nba")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    generate_html(all_games)
    print(f"Update Complete. {len(all_games)} stories processed.")

if __name__ == "__main__":
    main()
