import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
DAYS_BACK = 3
DAYS_AHEAD = 3

# Optional: Add your CricketData.org key here for deeper WC stats. 
# If empty, the script uses the ESPN Global Cricket feed (Free).
CRICKET_API_KEY = "52613cff-3da7-45f7-9793-a863aad4fb86" 

ALIASES = {
    "india": ["ind"], "namibia": ["nam"], "australia": ["aus"],
    "south africa": ["rsa", "sa"], "pakistan": ["pak"], "united states": ["usa"],
    "sri lanka": ["sl", "sri"], "italy": ["ita"], "clippers": ["lac"], "rockets": ["hou"]
}

def load_whitelist():
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                base = [line.strip().lower() for line in f if line.strip()]
                expanded = set(base)
                for item in base:
                    if item in ALIASES: expanded.update(ALIASES[item])
                return list(expanded)
    return ["india", "namibia", "clippers", "rockets", "sun devils", "asu"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    for item in whitelist:
        if re.search(r'\b' + re.escape(item) + r'\b', text_clean): return True
    return False

def get_verified_story(sport, league, event_id, home, away):
    """The Sleuth: Ensures the AP story actually belongs to this game."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
    try:
        data = requests.get(url, timeout=5).json()
        articles = data.get("news", {}).get("articles", [])
        for art in articles:
            content = art.get("story", art.get("description", ""))
            if is_match(content, [home, away, home.split()[-1], away.split()[-1]]):
                return re.sub('<[^<]+?>', '', content)
        
        header = data.get("header", {}).get("competitions", [{}])[0]
        if header.get("status", {}).get("type", {}).get("state") == "post":
            h_s = header['competitors'][0]['score']
            a_s = header['competitors'][1]['score']
            return f"**WIRE REPORT** — {home} and {away} wrapped up today's contest with a final of {h_s}-{a_s}. Analysis pending."
        return "The AP wire dispatch is currently being filed from the press box."
    except: return "Connection to the wire interrupted."

def get_cricket_data(whitelist):
    """Hits the ESPN Global Cricket feed to capture the T20 World Cup."""
    url = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/scoreboard"
    games = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist) or is_match(event.get("shortName", ""), whitelist):
                comp = event["competitions"][0]
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                
                h_name = home['team']['displayName']
                a_name = away['team']['displayName']
                
                # Format: Runs/Wickets (Overs)
                h_score = f"{home.get('score', '0')}/{home.get('wickets', '0')}"
                a_score = f"{away.get('score', '0')}/{away.get('wickets', '0')}"

                games.append({
                    "id": event['id'],
                    "sport": "T20 WORLD CUP",
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": h_name, "logo": home['team'].get("logo", ""), "score": h_score},
                    "away": {"name": a_name, "logo": away['team'].get("logo", ""), "score": a_score},
                    "story": f"**{event.get('name')}** — {event['status']['type']['detail']}. Follow live for over-by-over updates.",
                    "raw_date": event.get("date")
                })
        return games
    except: return []

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    date_str = f"{(datetime.now()-timedelta(days=DAYS_BACK)).strftime('%Y%m%d')}-{(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime('%Y%m%d')}"
    try:
        data = requests.get(url, params={"limit": "50", "dates": date_str}, timeout=10).json()
        games = []
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                comp = event["competitions"][0]
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                h_name, a_name = home['team']['displayName'], away['team']['displayName']
                
                games.append({
                    "id": event['id'],
                    "sport": league.upper().replace(".1", "").replace("-", " "),
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": h_name, "logo": home['team'].get("logo", ""), "score": home.get("score", "0")},
                    "away": {"name": a_name, "logo": away['team'].get("logo", ""), "score": away.get("score", "0")},
                    "story": get_verified_story(sport, league, event['id'], h_name, a_name),
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
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;900&display=swap">
        <style>
            :root {{ --bg: #050505; --accent: #ff3d00; --card: #121212; --text: #eee; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end; }}
            #live-clock {{ font-family: monospace; font-size: 1.4rem; color: var(--accent); }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .card-header {{ background: #1a1a1a; padding: 10px; font-size: 0.7rem; font-weight: 900; display: flex; justify-content: space-between; }}
            .score-area {{ display: flex; justify-content: space-around; align-items: center; padding: 30px 10px; text-align: center; }}
            .logo {{ width: 55px; height: 55px; object-fit: contain; background: transparent; margin-bottom: 10px; }}
            .score {{ font-size: 2.2rem; font-weight: 900; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 50px; max-height: 80vh; overflow-y: auto; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock">--:--:-- AZT</div></header>
    <div class="grid" id="main-grid"></div>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="border-bottom: 4px solid #111; padding-bottom: 10px; text-transform: uppercase;"></h2>
        <div id="modal-body" style="font-family: 'Georgia', serif; font-size: 1.2rem; line-height: 1.8;"></div>
    </div></div>
    <script>
        const games = {games_json};
        function updateClock() {{
            const now = new Date();
            const azt = now.toLocaleString('en-US', {{ timeZone: 'America/Phoenix', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }});
            document.getElementById('live-clock').innerText = azt + " AZT";
            
            document.querySelectorAll('.countdown').forEach(el => {{
                const target = new Date(el.dataset.date);
                const diff = target - now;
                if (diff > 0) {{
                    const h = Math.floor(diff / 3600000);
                    const m = Math.floor((diff % 3600000) / 60000);
                    el.innerText = `T-MINUS ${{h}}H ${{m}}M`;
                }} else {{
                    el.innerText = "LIVE / FINAL";
                }}
            }});
        }}
        setInterval(updateClock, 1000); updateClock();

        const grid = document.getElementById('main-grid');
        games.forEach(g => {{
            const card = document.createElement('div');
            card.className = 'card';
            const logoA = g.away.logo || `https://ui-avatars.com/api/?name=${{g.away.name}}&background=333&color=fff`;
            const logoH = g.home.logo || `https://ui-avatars.com/api/?name=${{g.home.name}}&background=333&color=fff`;
            
            card.innerHTML = `
                <div class="card-header"><span>${{g.sport}}</span><span class="countdown" data-date="${{g.raw_date}}"></span></div>
                <div class="score-area">
                    <div><img src="${{logoA}}" class="logo"><br><b>${{g.away.name}}</b><div class="score">${{g.away.score}}</div></div>
                    <div style="opacity:0.1; font-weight:900; font-size:1.5rem">VS</div>
                    <div><img src="${{logoH}}" class="logo"><br><b>${{g.home.name}}</b><div class="score">${{g.home.score}}</div></div>
                </div>
                <button class="btn-read" onclick="openModal('${{g.id}}')">READ DISPATCH</button>`;
            grid.appendChild(card);
        }});

        function openModal(id) {{
            const g = games.find(x => x.id === id);
            document.getElementById('modal-title').innerText = g.away.name + " @ " + g.home.name;
            document.getElementById('modal-body').innerHTML = g.story.replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>').replace(/\\n/g, '<br><br>');
            document.getElementById('modal').style.display = 'flex';
        }}
        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
    </script>
    </body></html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    
    # 1. Standard ESPN Leagues
    leagues = [("basketball", "nba"), ("hockey", "nhl"), ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey")]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist))
    
    # 2. Cricket World Cup 2026
    all_games.extend(get_cricket_data(whitelist))
    
    # Sort: Live first, then newest
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]), reverse=False)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
