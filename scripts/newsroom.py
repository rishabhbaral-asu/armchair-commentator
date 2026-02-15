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

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "250", "groups": "50" if "college" in league else "80", "cb": int(time.time())}
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = str(event['id'])
            if eid in seen_ids or not is_match(event.get("name", ""), whitelist): continue
            
            # Fetch deeper data for realistic stories
            sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
            s_data = requests.get(sum_url).json()
            
            # Extract Story Headlines or Recaps
            story = "No detailed report available yet."
            news = s_data.get("news", {}).get("articles", [])
            if news:
                story = news[0].get("description") or news[0].get("headline")
            elif event["status"]["type"]["state"] == "post":
                winner = next(t for t in event["competitions"][0]["competitors"] if t.get("winner"))
                story = f"FINAL: {winner['team']['displayName']} controlled the pace to secure the victory."

            comp = event["competitions"][0]
            games.append({
                "id": eid, 
                "league": league.upper().replace("-", " "),
                "status": event["status"]["type"]["state"],
                "home": {"name": comp['competitors'][0]['team']['shortDisplayName'], "score": comp['competitors'][0].get("score", "0")},
                "away": {"name": comp['competitors'][1]['team']['shortDisplayName'], "score": comp['competitors'][1].get("score", "0")},
                "story": story,
                "date": event["date"]  # UTC Format for Countdown
            })
            seen_ids.add(eid)
    except: pass
    return games

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now_str = datetime.now(az_tz).strftime("%A, %B %d, %Y")
    games_json = json.dumps(games)
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TEMPE TORCH | Sports Wire</title>
        <link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Oswald:wght@700&family=Inter:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {{ --gold: #FFC627; --maroon: #8C1D40; --dark: #121212; --card: #1E1E1E; }}
            body {{ background: var(--dark); color: #eee; font-family: 'Inter', sans-serif; margin: 0; padding: 20px; }}
            header {{ text-align: center; border-bottom: 3px solid var(--gold); padding-bottom: 20px; margin-bottom: 30px; }}
            h1 {{ font-family: 'UnifrakturMaguntia', serif; font-size: 5rem; color: var(--gold); margin: 0; }}
            .subhead {{ font-family: 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: 2px; }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }}
            .card {{ background: var(--card); border-left: 5px solid var(--maroon); padding: 20px; position: relative; cursor: pointer; transition: 0.3s; }}
            .card:hover {{ transform: translateY(-5px); background: #2a2a2a; }}
            
            .league-tag {{ font-size: 10px; font-weight: 800; color: var(--gold); background: #333; padding: 2px 6px; border-radius: 3px; }}
            .teams {{ font-size: 1.4rem; font-weight: 700; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; }}
            .score {{ font-family: 'Oswald', sans-serif; font-size: 2.2rem; color: #fff; }}
            
            .status-line {{ font-size: 12px; font-weight: bold; color: #888; border-top: 1px solid #333; padding-top: 10px; margin-top: 10px; }}
            .countdown {{ color: var(--gold); }}

            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 2000; overflow-y: auto; }}
            .modal-content {{ max-width: 600px; margin: 100px auto; padding: 20px; line-height: 1.6; font-size: 1.2rem; }}
            .close-btn {{ background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: 900; cursor: pointer; }}
        </style>
    </head>
    <body>
        <header>
            <h1>The Tempe Torch</h1>
            <div class="subhead">{now_str} | <span id="master-clock">00:00:00</span></div>
        </header>

        <div class="grid" id="main-grid"></div>

        <div id="modal">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal()">CLOSE WIRE</button>
                <h2 id="m-title" style="color:var(--gold); font-size: 2rem;"></h2>
                <p id="m-body"></p>
            </div>
        </div>

        <script>
            const games = {games_json};
            
            function updateClocks() {{
                const now = new Date();
                document.getElementById('master-clock').innerText = now.toLocaleTimeString('en-US', {{ hour12: false, timeZone: 'America/Phoenix' }}) + " MST";
                
                games.forEach(g => {{
                    if (g.status === 'pre') {{
                        const target = new Date(g.date);
                        const diff = target - now;
                        const el = document.getElementById('timer-' + g.id);
                        if (el) {{
                            if (diff > 0) {{
                                const h = Math.floor(diff / 3600000);
                                const m = Math.floor((diff % 3600000) / 60000);
                                const s = Math.floor((diff % 60000) / 1000);
                                el.innerText = `STARTS IN: ${{h}}h ${{m}}m ${{s}}s`;
                            }} else {{
                                el.innerText = "KICKOFF / STARTING";
                            }}
                        }}
                    }}
                }});
            }}

            const grid = document.getElementById('main-grid');
            games.forEach(g => {{
                const card = document.createElement('div');
                card.className = 'card';
                card.onclick = () => openModal(g);
                
                let statusHtml = g.status === 'pre' 
                    ? `<span id="timer-${{g.id}}" class="countdown">Calculating...</span>` 
                    : g.status === 'in' ? '<span style="color:#ff4d4d">● LIVE</span>' : 'FINAL';

                card.innerHTML = `
                    <span class="league-tag">${{g.league}}</span>
                    <div class="teams">
                        <span>${{g.away.name}} <br>at ${{g.home.name}}</span>
                        <span class="score">${{g.away.score}} - ${{g.home.score}}</span>
                    </div>
                    <div class="status-line">${{statusHtml}}</div>
                `;
                grid.appendChild(card);
            }});

            function openModal(g) {{
                document.getElementById('m-title').innerText = `${{g.away.name}} vs ${{g.home.name}}`;
                document.getElementById('m-body').innerText = g.story;
                document.getElementById('modal').style.display = 'block';
            }}
            function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
            
            setInterval(updateClocks, 1000);
            updateClocks();
        </script>
    </body>
    </html>
    """

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "nba"), ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("hockey", "nhl"), ("baseball", "mlb"), ("baseball", "college-baseball"), ("baseball", "college-softball"),
        ("soccer", "usa.mls"), ("soccer", "eng.1")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
