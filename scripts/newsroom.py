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
    return ["india", "namibia", "italy", "clippers", "rockets", "asu"]

def is_match(text, whitelist):
    if not text: return False
    text = text.lower()
    return any(w in text for w in whitelist)

def craft_ap_story(data, home, away):
    """The Narrative Engine: Analyzes box score data to write a human-like report."""
    header = data.get("header", {}).get("competitions", [{}])[0]
    status = header.get("status", {}).get("type", {})
    state = status.get("state")
    
    # 1. Use actual ESPN Recap if available
    for art in data.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # 2. Procedural Narrative (If no article exists)
    if state == "post":
        comp = header.get("competitors", [])
        winner = next((t for t in comp if t.get("winner")), comp[0])
        loser = next((t for t in comp if not t.get("winner")), comp[1])
        w_score, l_score = int(winner.get('score', 0)), int(loser.get('score', 0))
        
        # Determine victory vibe
        diff = w_score - l_score
        vibe = "dominated" if diff > 15 else "squeaked past" if diff < 5 else "controlled"
        
        # Get Star Player
        hero = ""
        for cat in data.get("leaders", []):
            if cat.get("name") in ["points", "goals", "runs"]:
                top = cat["leaders"][0]
                hero = f" {top['athlete']['displayName']} was instrumental, chipping in {top['displayValue']} during the decisive run."
                break
        
        return f"**{winner['team']['location'].upper()}** — The {winner['team']['displayName']} {vibe} the {loser['team']['displayName']} tonight, locking in a {w_score}-{l_score} victory.{hero} The wire is now closed on this event."

    # 3. Preview logic
    venue = data.get("gameInfo", {}).get("venue", {}).get("fullName", "an undisclosed arena")
    return f"**STADIUM DISPATCH** — All signs point to a physical contest at {venue} as the {away} prepare to battle the {home}. Local reports suggest a high-stakes atmosphere as tip-off approaches."

def get_cricket_wc(whitelist):
    """Scrapes the ICC feed using the teamInfo array for logos and names."""
    games = []
    # Both 'cricScore' for current and 'matches' for recent/upcoming
    for url in [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
                f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                # Check match name and teamInfo names
                t_info = m.get("teamInfo", [])
                t1_name = t_info[0]['name'] if len(t_info) > 0 else m.get("t1", "")
                t2_name = t_info[1]['name'] if len(t_info) > 1 else m.get("t2", "")
                
                if is_match(m.get("name", ""), whitelist) or is_match(t1_name, whitelist) or is_match(t2_name, whitelist):
                    logo_a = t_info[0]['img'] if len(t_info) > 0 else ""
                    logo_h = t_info[1]['img'] if len(t_info) > 1 else ""
                    
                    games.append({
                        "id": m['id'],
                        "sport": "T20 WORLD CUP",
                        "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": t2_name, "logo": logo_h, "score": m.get("t2s", "0/0")},
                        "away": {"name": t1_name, "logo": logo_a, "score": m.get("t1s", "0/0")},
                        "story": f"**PITCH REPORT** — {m.get('status')}. The wire is currently monitoring the match between {t1_name} and {t2_name}. Weather and ground conditions are reported as optimal.",
                        "raw_date": m.get("dateTimeGMT") or m.get("date")
                    })
        except: continue
    return games

def get_espn_data(sport, league, whitelist):
    """Fetches full slate (Finals & Upcoming) for February 12, 2026."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    # Date window: Yesterday through the Weekend
    params = {"dates": "20260211-20260215", "limit": "100"}
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
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
        <meta charset="UTF-8"><title>Tempe Torch | Wire</title>
        <style>
            :root {{ --bg: #050505; --accent: #ff3d00; --card: #121212; --text: #eee; }}
            body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
            #live-clock {{ font-family: monospace; font-size: 1.2rem; color: var(--accent); }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .card-header {{ background: #1a1a1a; padding: 10px; font-size: 0.7rem; font-weight: 900; display: flex; justify-content: space-between; color: #888; }}
            .score-area {{ display: flex; justify-content: space-around; padding: 25px; text-align: center; align-items: center; }}
            .logo {{ width: 45px; height: 45px; object-fit: contain; margin-bottom: 10px; background: #fff; padding: 5px; border-radius: 50%; }}
            .score {{ font-size: 2.2rem; font-weight: 900; letter-spacing: -1px; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 40px; border-radius: 2px; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock"></div></header>
    <div class="grid" id="main-grid"></div>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="border-bottom: 4px solid #111; padding-bottom: 10px; text-transform: uppercase;"></h2>
        <div id="modal-body" style="font-family: 'Georgia', serif; font-size: 1.25rem; line-height: 1.8;"></div>
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
            card.innerHTML = `<div class="card-header"><span>${{g.sport}}</span><span>${{g.status.toUpperCase()}}</span></div>
                <div class="score-area">
                    <div><img src="${{g.away.logo}}" class="logo" onerror="this.src='https://ui-avatars.com/api/?name=${{g.away.name}}'"><br><b>${{g.away.name}}</b><div class="score">${{g.away.score}}</div></div>
                    <div style="opacity:0.2; font-weight:900">VS</div>
                    <div><img src="${{g.home.logo}}" class="logo" onerror="this.src='https://ui-avatars.com/api/?name=${{g.home.name}}'"><br><b>${{g.home.name}}</b><div class="score">${{g.home.score}}</div></div>
                </div>
                <button class="btn-read" onclick="openModal('${{g.id}}')">OPEN WIRE DISPATCH</button>`;
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
    
    # 1. ESPN Major Slate
    for s, l in [("basketball", "nba"), ("hockey", "nhl"), ("basketball", "mens-college-basketball")]:
        all_games.extend(get_espn_data(s, l, whitelist))
    
    # 2. Cricket World Cup
    all_games.extend(get_cricket_wc(whitelist))
    
    # Sort: Current/Upcoming first, then by date
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
