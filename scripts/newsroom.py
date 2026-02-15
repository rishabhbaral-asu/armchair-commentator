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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium", "iowa",
        "indiana", "illinois"
    ]

# --- 2. ENGINES ---
def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        if res.get("cod") == 200:
            return f"{round(res['main']['temp'])}°F and {res['weather'][0]['description']}"
    except: pass
    return "Clear Skies"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    city = comp.get("venue", {}).get("address", {}).get("city", "Tempe")
    weather = get_live_weather(city)
    
    # PREGAME PREVIEW
    if status_type == "STATUS_SCHEDULED":
        time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
        return f"**{city.upper()}** — Anticipation is high at {comp.get('venue', {}).get('fullName', 'the arena')} as {away['team']['shortDisplayName']} visits {home['team']['shortDisplayName']}. Current local weather is {weather}. Fans in {city} are prepping for a {time_ms.strftime('%I:%M %p')} MST start."

    # LIVE IN-PROGRESS
    if status_type == "STATUS_IN_PROGRESS":
        clock = event["status"]["type"]["detail"]
        return f"**LIVE FROM {city.upper()}** — Intense action underway! The score is {away['score']} - {home['score']} with {clock} remaining. Both sides are battling for control in {city} as momentum shifts with every possession."

    # POSTGAME RECAP
    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    diff = abs(int(home['score']) - int(away['score']))
    margin = "in a thrilling nail-biter" if diff < 5 else "decisively"
    
    return f"**{city.upper()} (AP)** — The {winner['team']['shortDisplayName']} protected their home turf today, defeating {loser['team']['shortDisplayName']} {winner['score']}-{loser['score']} {margin}. The atmosphere in {city} was electric as the hosts secured the win."

# --- 3. DATA FETCH ---
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
    except: pass
    return results

# --- 4. HTML GENERATION ---
def generate_html(games):
    now_str = datetime.now(MST).strftime("%B %d, %Y")
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{ --bg: #0b0d0f; --card: #161a1e; --accent: #ffc627; --text: #eee; --dim: #888; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }}
            .container {{ max-width: 850px; margin: auto; }}
            .header {{ text-align: center; border-bottom: 2px solid var(--accent); padding-bottom: 20px; margin-bottom: 40px; }}
            .live-clock {{ font-family: monospace; color: var(--accent); font-size: 1.4em; margin-top: 10px; }}
            .card {{ background: var(--card); border-radius: 12px; margin-bottom: 30px; border: 1px solid #2d3238; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
            .card-header {{ background: #222; padding: 12px 20px; display: flex; justify-content: space-between; font-weight: bold; font-size: 0.9em; border-bottom: 1px solid #333; }}
            .scoreboard {{ display: flex; align-items: center; justify-content: space-around; padding: 35px 20px; }}
            .team {{ text-align: center; width: 33%; }}
            .team img {{ height: 85px; filter: drop-shadow(0 0 8px rgba(255,198,39,0.1)); }}
            .score-val {{ font-size: 3.5em; font-weight: 900; letter-spacing: -2px; }}
            .story {{ padding: 30px; line-height: 1.8; font-size: 1.15em; background: rgba(255,255,255,0.02); }}
            .countdown {{ color: #ff4757; font-family: monospace; }}
            .status-live {{ color: #2ecc71; animation: blink 2s infinite; }}
            @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-family: serif; font-size: 3.5em;">THE ARMCHAIR COMMENTATOR</h1>
                <div id="wall-clock" class="live-clock">Loading Clock...</div>
                <p style="color:var(--dim); margin-top:5px;">{now_str}</p>
            </div>
    """
    
    if not games:
        html += "<p style='text-align:center; color:var(--dim);'>No scheduled games on your watchlist today.</p>"

    for g in games:
        # Determine status style
        status_html = f"<span>{g['status_text']}</span>"
        if g['status_type'] == "STATUS_SCHEDULED":
            status_html = f"<span class='countdown' data-time='{g['iso_date']}'>Calculating...</span>"
        elif g['status_type'] == "STATUS_IN_PROGRESS":
            status_html = f"<span class='status-live'>● {g['status_text']}</span>"

        html += f"""
        <div class="card">
            <div class="card-header">
                <span>{g['headline']}</span>
                {status_html}
            </div>
            <div class="scoreboard">
                <div class="team"><img src="{g['away_logo']}"><br><b>{g['away_name']}</b></div>
                <div class="score-val">{g['away_score']} - {g['home_score']}</div>
                <div class="team"><img src="{g['home_logo']}"><br><b>{g['home_name']}</b></div>
            </div>
            <div class="story">{g['story']}</div>
        </div>
        """

    html += """
        </div>
        <script>
            function updateClocks() {
                // 1. Digital Wall Clock (MST)
                const now = new Date();
                const mst = now.toLocaleTimeString('en-US', {timeZone: 'America/Phoenix', hour12: true});
                document.getElementById('wall-clock').innerHTML = mst + " MST";

                // 2. Countdown Engine
                document.querySelectorAll('.countdown').forEach(el => {
                    const target = new Date(el.getAttribute('data-time')).getTime();
                    const dist = target - now.getTime();
                    if (dist < 0) { el.innerHTML = "LIVE"; return; }
                    const h = Math.floor(dist / (1000 * 60 * 60));
                    const m = Math.floor((dist % (1000 * 60 * 60)) / (1000 * 60));
                    const s = Math.floor((dist % (1000 * 60)) / 1000);
                    el.innerHTML = "STARTS IN: " + h + "h " + m + "m " + s + "s";
                });
            }
            setInterval(updateClocks, 1000);
            updateClocks();
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [("basketball", "mens-college-basketball"), ("basketball", "nba"), ("baseball", "college-baseball"), ("basketball", "womens-college-basketball"), ("hockey", "mens-college-hockey"), ("hockey", "nhl")]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    generate_html(all_games)
    print(f"Generated Live Newsroom with {len(all_games)} matches.")

if __name__ == "__main__": main()
