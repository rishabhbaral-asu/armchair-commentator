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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium"
    ]
# --- ENGINES ---
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
    
    # Extract Records & Rankings
    h_rank = home.get("curatedRank", {}).get("current", 99)
    a_rank = away.get("curatedRank", {}).get("current", 99)
    h_rank_str = f"No. {h_rank} " if h_rank <= 25 else ""
    a_rank_str = f"No. {a_rank} " if a_rank <= 25 else ""
    
    h_rec = next((r["summary"] for r in home.get("records", []) if r["type"] == "total"), "0-0")
    a_rec = next((r["summary"] for r in away.get("records", []) if r["type"] == "total"), "0-0")
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Tempe")
    venue_name = comp.get("venue", {}).get("fullName", "the arena")
    weather = get_live_weather(city)

    # PREGAME: ESPN Analytical Style
    if status_type == "STATUS_SCHEDULED":
        time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
        
        # Pull Top Performers if available in the API response
        try:
            h_leader = home["leaders"][0]["leaders"][0]["athlete"]["displayName"]
            a_leader = away["leaders"][0]["leaders"][0]["athlete"]["displayName"]
            leader_str = f"TOP PERFORMERS: {h_leader} leads the charge for the hosts, while {a_leader} anchors the visitors."
        except:
            leader_str = "Both teams look to find an edge in this conference matchup."

        return f"""
        <b>{a_rank_str}{away['team']['displayName']} ({a_rec}) at {h_rank_str}{home['team']['displayName']} ({h_rec})</b><br>
        {city}, {comp.get('venue', {}).get('address', {}).get('state', 'ST')}; {time_ms.strftime('%A, %I:%M %p')} MST<br><br>
        <b>BOTTOM LINE:</b> {h_rank_str}{home['team']['shortDisplayName']} hosts {away['team']['shortDisplayName']} at {venue_name}. 
        The local weather in {city} is {weather}. {leader_str}<br><br>
        The teams meet for the first time in conference play this season. {home['team']['shortDisplayName']} currently averages strong production at home, 
        while {away['team']['shortDisplayName']} has shown resilience in tight games decided by 5 points or fewer.
        """

    # LIVE: ESPN Gamecast Style
    if status_type == "STATUS_IN_PROGRESS":
        clock = event["status"]["type"]["detail"]
        return f"<b>LIVE UPDATING:</b> {away['team']['shortDisplayName']} vs {home['team']['shortDisplayName']}. Currently at {venue_name}. The score stands at {away['score']} - {home['score']} with {clock} left. {away['team']['shortDisplayName']} is fighting for a key road win to improve their {a_rec} record."

    # POSTGAME: Recap Style
    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    return f"<b>FINAL:</b> {winner['team']['shortDisplayName']} defeated {loser['team']['shortDisplayName']} {winner['score']}-{loser['score']}. {winner['team']['shortDisplayName']} improves to {winner.get('records', [{}])[0].get('summary', 'N/A')} with the victory in {city}."

# --- DATA FETCH ---
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
                    "id": eid,
                    "headline": event.get("name"),
                    "home_logo": event["competitions"][0]["competitors"][0]["team"].get("logo"),
                    "away_logo": event["competitions"][0]["competitors"][1]["team"].get("logo"),
                    "home_name": event["competitions"][0]["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": event["competitions"][0]["competitors"][1]["team"]["shortDisplayName"],
                    "home_score": event["competitions"][0]["competitors"][0].get("score", "0"),
                    "away_score": event["competitions"][0]["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "status_type": event["status"]["type"]["name"],
                    "iso_date": event["date"], 
                    "story": craft_dynamic_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- HTML GENERATION ---
def generate_html(games):
    now_str = datetime.now(MST).strftime("%B %d, %Y")
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {{ --bg: #0b0d0f; --card: #161a1e; --accent: #ffc627; --text: #eee; --dim: #888; }}
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }}
            .container {{ max-width: 900px; margin: auto; }}
            .header {{ text-align: left; border-bottom: 3px solid var(--accent); padding-bottom: 10px; margin-bottom: 40px; }}
            .live-clock {{ font-family: monospace; color: var(--accent); font-size: 1.2em; float: right; }}
            .card {{ background: var(--card); border-radius: 4px; margin-bottom: 30px; border-left: 5px solid var(--accent); overflow: hidden; }}
            .card-header {{ background: #222; padding: 10px 20px; font-weight: bold; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; color: var(--dim); border-bottom: 1px solid #333; }}
            .scoreboard {{ display: flex; align-items: center; padding: 30px; background: #1c2126; }}
            .team {{ display: flex; align-items: center; width: 40%; }}
            .team img {{ height: 60px; margin-right: 20px; }}
            .team-info {{ font-size: 1.5em; font-weight: bold; }}
            .score-val {{ width: 20%; text-align: center; font-size: 3em; font-weight: 900; color: var(--accent); }}
            .story {{ padding: 30px; line-height: 1.6; font-size: 1em; border-top: 1px solid #2d3238; }}
            .countdown {{ color: #ff4757; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span id="wall-clock" class="live-clock"></span>
                <h1 style="margin:0; font-size: 2.5em; font-weight: 900;">DIGITAL NEWSROOM</h1>
                <p style="margin:0; color:var(--dim); font-weight: bold;">{now_str} • MST EDITION</p>
            </div>
    """
    for g in games:
        status_html = f"<span>{g['status_text']}</span>"
        if g['status_type'] == "STATUS_SCHEDULED":
            status_html = f"<span class='countdown' data-time='{g['iso_date']}'>COUNTDOWN</span>"

        html += f"""
        <div class="card">
            <div class="card-header">
                {g['headline']} — {status_html}
            </div>
            <div class="scoreboard">
                <div class="team"><img src="{g['away_logo']}"><div class="team-info">{g['away_name']}</div></div>
                <div class="score-val">{g['away_score']} - {g['home_score']}</div>
                <div class="team" style="flex-direction: row-reverse; text-align: right;"><img src="{g['home_logo']}" style="margin-right:0; margin-left:20px;"><div class="team-info">{g['home_name']}</div></div>
            </div>
            <div class="story">{g['story']}</div>
        </div>
        """

    html += """
        </div>
        <script>
            function update() {
                const now = new Date();
                document.getElementById('wall-clock').innerHTML = now.toLocaleTimeString('en-US', {timeZone: 'America/Phoenix', hour12: true}) + " MST";
                document.querySelectorAll('.countdown').forEach(el => {
                    const target = new Date(el.getAttribute('data-time')).getTime();
                    const dist = target - now.getTime();
                    if (dist < 0) { el.innerHTML = "LIVE"; return; }
                    const h = Math.floor(dist / (1000 * 60 * 60));
                    const m = Math.floor((dist % (1000 * 60 * 60)) / (1000 * 60));
                    const s = Math.floor((dist % (1000 * 60)) / 1000);
                    el.innerHTML = "T-MINUS " + h + ":" + (m<10?'0':'') + m + ":" + (s<10?'0':'') + s;
                });
            }
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
    leagues = [("basketball", "mens-college-basketball"), ("basketball", "nba")]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    generate_html(all_games)

if __name__ == "__main__": main()
