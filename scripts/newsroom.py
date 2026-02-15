import requests
import json
from datetime import datetime
import pytz
import os
import re
import time

# --- CONFIG ---
OUTPUT_FILE = "index.html"

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

def is_match(event_name, whitelist):
    if not event_name: return False
    name_clean = event_name.lower()
    return any(re.search(r'\b' + re.escape(team) + r'\b', name_clean) for team in whitelist)

def craft_ap_story(summary_json):
    header = summary_json.get("header", {})
    comp = header.get("competitions", [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state")
    teams = comp.get("competitors", [])
    for art in summary_json.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))
    if state == "post":
        winner = next((t for t in teams if t.get("winner")), teams[0])
        loser = next((t for t in teams if not t.get("winner")), teams[1])
        return f"**{winner['team']['location'].upper()}** — The {winner['team']['displayName']} secured the win over the {loser['team']['displayName']}."
    return "WIRE DISPATCH — Event in progress or scheduled. Final reports pending."

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "200", "cb": int(time.time())}
    if "college-" in league: params["groups"] = "50"
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = str(event['id'])
            if eid in seen_ids or not is_match(event.get("name", ""), whitelist): continue
            sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
            summary = requests.get(sum_url).json()
            comp = event["competitions"][0]
            home, away = comp['competitors'][0], comp['competitors'][1]
            seen_ids.add(eid)
            games.append({
                "id": eid, "sport": league.upper().replace("-", " "), 
                "status": event["status"]["type"]["state"],
                "home": {"name": home['team']['displayName'], "score": home.get("score", "0")},
                "away": {"name": away['team']['displayName'], "score": away.get("score", "0")},
                "story": craft_ap_story(summary), "raw_date": event.get("date")
            })
    except: pass
    return games

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now = datetime.now(az_tz).strftime("%B %d, %Y")
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>The Tempe Torch</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@900&family=Inter:wght@400;700&family=Georgia&display=swap">
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #fdfdfd; padding: 40px; color: #111; }}
            header {{ text-align: center; border-bottom: 5px double #000; margin-bottom: 40px; }}
            h1 {{ font-family: 'Playfair Display', serif; font-size: 3.5rem; text-transform: uppercase; margin: 0; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ border: 1px solid #ccc; padding: 20px; background: #fff; cursor: pointer; }}
            .score {{ font-family: 'Playfair Display', serif; font-size: 2rem; margin: 10px 0; }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: white; z-index: 1000; overflow-y: auto; padding: 50px; box-sizing: border-box; }}
            .story-body {{ font-family: 'Georgia', serif; font-size: 1.2rem; line-height: 1.6; max-width: 700px; margin: auto; }}
        </style>
    </head>
    <body>
        <header><h1>The Tempe Torch</h1><p>{now}</p></header>
        <div class="grid" id="grid"></div>
        <div id="modal"><button onclick="closeModal()">CLOSE</button><div id="m-content" class="story-body"></div></div>
        <script>
            const games = {games_json};
            const grid = document.getElementById('grid');
            if(games.length === 0) grid.innerHTML = "<h3>No wire updates for your whitelist teams at this hour.</h3>";
            games.forEach(g => {{
                const d = document.createElement('div'); d.className = 'card'; d.onclick = () => openModal(g.id);
                d.innerHTML = `<b>${{g.sport}}</b><br>${{g.away.name}} @ ${{g.home.name}}<div class="score">${{g.away.score}} - ${{g.home.score}}</div>`;
                grid.appendChild(d);
            }});
            function openModal(id) {{ 
                const g = games.find(x => x.id === id); 
                document.getElementById('m-content').innerHTML = `<h2>${{g.away.name}} vs ${{g.home.name}}</h2><hr><p>${{g.story}}</p>`;
                document.getElementById('modal').style.display = 'block'; 
            }}
            function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
        </script>
    </body></html>"""

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "nba"), ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("hockey", "nhl"), ("hockey", "mens-college-hockey"),
        ("baseball", "mlb"), ("baseball", "college-baseball"), ("baseball", "college-softball"),
        ("football", "nfl"), ("soccer", "usa.mls"), ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "ita.1")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
