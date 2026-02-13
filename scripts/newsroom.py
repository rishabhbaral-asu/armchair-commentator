import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIG ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
CRICKET_API_KEY = "52613cff-3da7-45f7-9793-a863aad4fb86"

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            return [l.strip().lower() for l in f if l.strip()]
    return ["india", "namibia", "italy", "nepal", "clippers", "rockets", "asu"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    return any(w in text_clean for w in whitelist)

def craft_ap_story(data, home, away):
    """The AP Engine: Analyzes box score data to write a human-like report."""
    header = data.get("header", {}).get("competitions", [{}])[0]
    state = header.get("status", {}).get("type", {}).get("state")
    
    # 1. PRIORITY: REAL JOURNALISM
    for art in data.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # 2. GENERATIVE NARRATIVE (POST-GAME)
    if state == "post":
        comp = header.get("competitors", [])
        winner = next((t for t in comp if t.get("winner")), comp[0])
        loser = next((t for t in comp if not t.get("winner")), comp[1])
        w_score, l_score = int(winner.get('score', 0)), int(loser.get('score', 0))
        
        diff = w_score - l_score
        vibe = "routed" if diff > 18 else "edged" if diff < 6 else "defeated"
        
        hero = ""
        for cat in data.get("leaders", []):
            if cat.get("name") in ["points", "goals", "runs"]:
                top = cat["leaders"][0]
                hero = f" {top['athlete']['displayName']} was the standout, finishing with {top['displayValue']}."
                break
        
        return f"**{winner['team']['location'].upper()}** — The {winner['team']['displayName']} {vibe} the {loser['team']['displayName']} in a {w_score}-{l_score} final.{hero} Wire reports indicate the locker room is high-energy following the result."

    # 3. PREVIEW
    venue = data.get("gameInfo", {}).get("venue", {}).get("fullName", "the arena")
    return f"**STADIUM DISPATCH** — All eyes are on {venue} as the {away} arrive to face the {home}. The wire suggests a high-stakes atmosphere for this scheduled clash."

def get_cricket_wc(whitelist):
    """STRICT FILTER: Only pulls teams on your whitelist using the teamInfo array."""
    games = []
    # Endpoint 1: Live Scores | Endpoint 2: Full Match List
    for url in [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
                f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                t_info = m.get("teamInfo", [])
                t1 = t_info[0] if len(t_info) > 0 else {"name": m.get("t1", ""), "img": ""}
                t2 = t_info[1] if len(t_info) > 1 else {"name": m.get("t2", ""), "img": ""}
                
                # STRICT WHITELIST CHECK
                if is_match(t1['name'], whitelist) or is_match(t2['name'], whitelist):
                    games.append({
                        "id": m['id'],
                        "sport": "T20 WORLD CUP",
                        "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": t2['name'], "logo": t2.get('img', ""), "score": m.get("t2s", "0/0")},
                        "away": {"name": t1['name'], "logo": t1.get('img', ""), "score": m.get("t1s", "0/0")},
                        "story": f"**PITCH DISPATCH** — {m.get('status')}. Reporting on {t1['name']} vs {t2['name']}. Conditions are consistent with professional T20 standards.",
                        "raw_date": m.get("dateTimeGMT") or m.get("date")
                    })
        except: continue
    return games

def get_espn_data(sport, league, whitelist):
    """Pulls everything from yesterday's finals to this weekend's upcoming games."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    # February 12, 2026 Window: Feb 11 to Feb 15
    params = {"dates": "20260211-20260215", "limit": "100"}
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                # Dig deeper into 'summary' for the Story Engine
                sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event['id']}"
                summary = requests.get(sum_url).json()
                
                comp = event["competitions"][0]
                home, away = comp['competitors'][0], comp['competitors'][1]
                
                games.append({
                    "id": event['id'],
                    "sport": league.upper(),
                    "status": event["status"]["type"]["state"],
                    "home": {"name": home['team']['displayName'], "logo": home['team'].get("logo", ""), "score": home.get("score", "0")},
                    "away": {"name": away['team']['displayName'], "logo": away['team'].get("logo", ""), "score": away.get("score", "0")},
                    "story": craft_ap_story(summary, home['team']['displayName'], away['team']['displayName']),
                    "raw_date": event.get("date")
                })
        return games
    except: return []

def generate_html(games):
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>Tempe Torch | Wire Service</title>
        <style>
            :root {{ --bg: #050505; --accent: #ff3d00; --card: #121212; --text: #eee; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end; }}
            h1 span {{ font-weight: 100; color: #666; }}
            #live-clock {{ font-family: monospace; font-size: 1.2rem; color: var(--accent); }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .card-header {{ background: #1a1a1a; padding: 10px; font-size: 0.7rem; font-weight: 900; display: flex; justify-content: space-between; }}
            .score-area {{ display: flex; justify-content: space-around; padding: 25px; text-align: center; align-items: center; }}
            .logo {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 8px; background: #fff; border-radius: 50%; padding: 4px; }}
            .score {{ font-size: 2.3rem; font-weight: 900; letter-spacing: -2px; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 50px; border-radius: 2px; position: relative; max-height: 80vh; overflow-y: auto; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock">--:--:-- AZT</div></header>
    <div class="grid" id="main-grid"></div>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="border-bottom: 4px solid #111; padding-bottom: 10px; text-transform: uppercase;"></h2>
        <div id="modal-body" style="font-family: 'Georgia', serif; font-size: 1.3rem; line-height: 1.8;"></div>
    </div></div>
    <script>
        const games = {games_json};
        function updateClock() {{
            const now = new Date();
            document.getElementById('live-clock').innerText = now.toLocaleString('en-US', {{ timeZone: 'America/Phoenix', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }}) + " AZT";
        }}
        setInterval(updateClock, 1000); updateClock();

        const grid = document.getElementById('main-grid');
        games.forEach(g => {{
            const card = document.createElement('div');
            card.className = 'card';
            const logoA = g.away.logo || `https://ui-avatars.com/api/?name=${{g.away.name}}&background=333&color=fff`;
            const logoH = g.home.logo || `https://ui-avatars.com/api/?name=${{g.home.name}}&background=333&color=fff`;
            card.innerHTML = `<div class="card-header"><span>${{g.sport}}</span><span>${{g.status.toUpperCase()}}</span></div>
                <div class="score-area">
                    <div><img src="${{logoA}}" class="logo"><br><b>${{g.away.name}}</b><div class="score">${{g.away.score}}</div></div>
                    <div style="opacity:0.2; font-weight:900">VS</div>
                    <div><img src="${{logoH}}" class="logo"><br><b>${{g.home.name}}</b><div class="score">${{g.home.score}}</div></div>
                </div>
                <button class="btn-read" onclick="openModal('${{g.id}}')">READ DISPATCH</button>`;
            grid.appendChild(card);
        }});

        function openModal(id) {{
            const g = games.find(x => x.id === id);
            document.getElementById('modal-title').innerText = g.away.name + " @ " + g.home.name;
            document.getElementById('modal-body').innerHTML = g.story.replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>');
            document.getElementById('modal').style.display = 'flex';
        }}
        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
    </script>
    </body></html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    
    # Standard ESPN (NBA, NHL, College)
    for s, l in [("basketball", "nba"), ("hockey", "nhl"), ("basketball", "mens-college-basketball")]:
        all_games.extend(get_espn_data(s, l, whitelist))
    
    # Cricket World Cup (Strict Filter)
    all_games.extend(get_cricket_wc(whitelist))
    
    # Sort: Live first, then by date (most recent first)
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
