import requests
import json
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIG ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium",
        "indiana", "illinois", "iowa", "hoosiers", "illini"
    ]

# --- 2. ENGINES ---
def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        if res.get("cod") == 200:
            return f"{round(res['main']['temp'])}°F and {res['weather'][0]['description']}"
    except: pass
    return "Variable Conditions"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    h_rank = home.get("curatedRank", {}).get("current", 99)
    a_rank = away.get("curatedRank", {}).get("current", 99)
    h_rank_str = f"No. {h_rank} " if h_rank <= 25 else ""
    a_rank_str = f"No. {a_rank} " if a_rank <= 25 else ""
    
    h_rec = next((r["summary"] for r in home.get("records", []) if r["type"] == "total"), "0-0")
    a_rec = next((r["summary"] for r in away.get("records", []) if r["type"] == "total"), "0-0")
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Tempe")
    venue_name = comp.get("venue", {}).get("fullName", "the arena")
    weather = get_live_weather(city)

    # Analytics / Odds
    odds_str = ""
    if "odds" in comp:
        odds_str = f"<b>LINE:</b> {comp['odds'][0].get('details', 'Even')}. "

    if status_type == "STATUS_SCHEDULED":
        time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
        return f"""
        <b>{a_rank_str}{away['team']['displayName']} ({a_rec}) at {h_rank_str}{home['team']['displayName']} ({h_rec})</b><br>
        {city}, {comp.get('venue', {}).get('address', {}).get('state', 'ST')}; {time_ms.strftime('%A, %I:%M %p')} MST<br><br>
        <b>BOTTOM LINE:</b> {h_rank_str}{home['team']['shortDisplayName']} hosts {away['team']['shortDisplayName']} at {venue_name}. 
        {odds_str}The local weather in {city} is {weather}. Both teams look to capitalize on key conference positioning in this Sunday matchup.
        """
    
    if status_type == "STATUS_IN_PROGRESS":
        clock = event["status"]["type"]["detail"]
        return f"<b>LIVE FROM {city.upper()}:</b> The {away['team']['shortDisplayName']} ({away['score']}) and {home['team']['shortDisplayName']} ({home['score']}) are locked in a battle at {venue_name}. Game Clock: {clock}. {away['team']['shortDisplayName']} is currently looking to improve their {a_rec} record with a statement road win."

    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    return f"<b>FINAL:</b> {winner['team']['shortDisplayName']} defended home court with a win over {loser['team']['shortDisplayName']} in {city}. Final Score: {winner['score']}-{loser['score']}."

# --- 3. DATA FETCH ---
def get_espn_data(sport, league, whitelist, seen_ids):
    # Base URL
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    
    # 1. Expand the search window (Today + Next 3 days)
    now = datetime.now(MST)
    start_date = now.strftime("%Y%m%d")
    end_date = (now + timedelta(days=3)).strftime("%Y%m%d")
    
    params = {
        "limit": "500",  # 2. Increase limit to see all games
        "dates": f"{start_date}-{end_date}" # 3. Date range
    }
    
    # 4. Special fix for College Basketball to see non-ranked teams
    if league == "mens-college-basketball":
        params["groups"] = "50" 

    results = []
    try:
        # Use params in the request
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        for event in data.get("events", []):
            eid = event["id"]
            comp = event["competitions"][0]
            
            # Extract names for matching
            search_blob = []
            for t in comp["competitors"]:
                team_obj = t["team"]
                search_blob.extend([
                    team_obj.get("shortDisplayName", "").lower(),
                    team_obj.get("displayName", "").lower(),
                    team_obj.get("name", "").lower(),
                    team_obj.get("abbreviation", "").lower()
                ])
            
            # Combine whitelist match
            full_blob = " ".join(search_blob)
            match_found = any(team.lower() in full_blob for team in whitelist)

            if match_found and eid not in seen_ids:
                results.append({
                    "id": eid,
                    "headline": event.get("name"),
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "status_type": event["status"]["type"]["name"],
                    "iso_date": event["date"], 
                    "story": craft_dynamic_story(event, sport, league)
                })
                seen_ids.add(eid)
    except Exception as e:
        print(f"Error fetching {league}: {e}")
    return results

# --- 4. HTML GENERATION ---
def generate_html(games):
    now_dt = datetime.now(MST)
    update_time = now_dt.strftime("%I:%M:%S %p")
    now_str = now_dt.strftime("%B %d, %Y")
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{ --bg: #0b0d0f; --card: #161a1e; --accent: #ffc627; --text: #eee; --dim: #888; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }}
            .container {{ max-width: 900px; margin: auto; }}
            .header {{ text-align: left; border-bottom: 3px solid var(--accent); padding-bottom: 15px; margin-bottom: 40px; position: relative; }}
            .live-clock {{ font-family: monospace; color: var(--accent); font-size: 1.3em; position: absolute; right: 0; top: 0; }}
            .card {{ background: var(--card); border-radius: 4px; margin-bottom: 30px; border-left: 6px solid var(--accent); transition: transform 0.2s; }}
            .card:hover {{ transform: scale(1.01); }}
            .card-header {{ background: #222; padding: 12px 20px; font-weight: 800; font-size: 0.8em; text-transform: uppercase; color: var(--dim); border-bottom: 1px solid #333; }}
            .scoreboard {{ display: flex; align-items: center; padding: 25px 35px; background: #1c2126; }}
            .team {{ display: flex; align-items: center; width: 40%; }}
            .team img {{ height: 55px; margin-right: 18px; }}
            .score-val {{ width: 20%; text-align: center; font-size: 2.8em; font-weight: 900; color: var(--accent); text-shadow: 0 0 10px rgba(255,198,39,0.2); }}
            .story {{ padding: 30px; line-height: 1.7; font-size: 1.05em; border-top: 1px solid #2d3238; color: #ccc; }}
            .countdown {{ color: #ff4757; font-weight: bold; letter-spacing: 1px; }}
            .footer {{ text-align: center; color: var(--dim); font-size: 0.8em; margin-top: 50px; border-top: 1px solid #333; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div id="wall-clock" class="live-clock">--:--:--</div>
                <h1 style="margin:0; font-size: 2.8em; font-weight: 900; letter-spacing: -1px;">NEWSROOM WIRE</h1>
                <p style="margin:0; color:var(--dim); font-weight: bold;">{now_str} • REFRESHED AT {update_time} MST</p>
            </div>
    """
    
    if not games:
        html += "<div style='text-align:center; padding:50px; color:var(--dim);'><h3>Scanning the wires... no matches found for your whitelist.</h3></div>"

    for g in games:
        status_display = f"<span>{g['status_text']}</span>"
        if g['status_type'] == "STATUS_SCHEDULED":
            status_display = f"<span class='countdown' data-time='{g['iso_date']}'>INITIALIZING...</span>"
        elif g['status_type'] == "STATUS_IN_PROGRESS":
            status_display = f"<span style='color:#2ecc71; animation: pulse 2s infinite;'>● LIVE: {g['status_text']}</span>"

        html += f"""
        <div class="card">
            <div class="card-header">{g['headline']} — {status_display}</div>
            <div class="scoreboard">
                <div class="team"><img src="{g['away_logo']}"><div style="font-size:1.4em; font-weight:bold;">{g['away_name']}</div></div>
                <div class="score-val">{g['away_score']} - {g['home_score']}</div>
                <div class="team" style="flex-direction: row-reverse; text-align: right;"><img src="{g['home_logo']}" style="margin-left:18px; margin-right:0;"><div style="font-size:1.4em; font-weight:bold;">{g['home_name']}</div></div>
            </div>
            <div class="story">{g['story']}</div>
        </div>"""

    html += f"""
            <div class="footer">
                Data provided by ESPN API & OpenWeather • System Last Sync: {update_time} MST
            </div>
        </div>
        <script>
            function update() {{
                const now = new Date();
                // Update Master Clock
                document.getElementById('wall-clock').innerHTML = now.toLocaleTimeString('en-US', {{timeZone: 'America/Phoenix', hour12: true}});
                
                // Update Individual Countdowns
                document.querySelectorAll('.countdown').forEach(el => {{
                    const target = new Date(el.getAttribute('data-time')).getTime();
                    const dist = target - now.getTime();
                    if (dist < 0) {{ el.innerHTML = "LIVE"; return; }}
                    const h = Math.floor(dist / 3600000);
                    const m = Math.floor((dist % 3600000) / 60000);
                    const s = Math.floor((dist % 60000) / 1000);
                    el.innerHTML = "T-MINUS " + h + ":" + (m<10?'0':'') + m + ":" + (s<10?'0':'') + s;
                }});
            }}
            setInterval(update, 1000);
            update();
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"),
        ("basketball", "nba"),
        ("hockey", "nhl"),
        ("soccer", "usa.mls"),
        ("soccer", "eng.1"),
        ("baseball", "mlb"),
        ("football", "nfl")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    # Sort games by date
    all_games.sort(key=lambda x: x['iso_date'])
    
    generate_html(all_games)
    print(f"Update Success: {len(all_games)} articles generated at index.html")

if __name__ == "__main__": main()
