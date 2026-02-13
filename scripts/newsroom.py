import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
CRICKET_API_KEY = "52613cff-3da7-45f7-9793-a863aad4fb86"

# Mapping for the ICC T20 World Cup 2026
ALIASES = {
    "india": ["ind"], "namibia": ["nam"], "australia": ["aus"],
    "south africa": ["rsa", "sa"], "pakistan": ["pak"], "united states": ["usa"],
    "sri lanka": ["sl", "sri"], "italy": ["ita"], "nepal": ["nep"]
}

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            base = [l.strip().lower() for l in f if l.strip()]
            expanded = set(base)
            for k, v in ALIASES.items():
                if k in base: expanded.update(v)
            return list(expanded)
    return ["india", "namibia", "clippers", "rockets", "asu"]

def is_match(text, whitelist):
    if not text: return False
    return any(re.search(r'\b' + re.escape(w) + r'\b', text.lower()) for w in whitelist)

def craft_ap_story(data, home, away, sport_type="major"):
    """The Narrative Engine: Writes human-like recaps and previews."""
    header = data.get("header", {}).get("competitions", [{}])[0]
    state = header.get("status", {}).get("type", {}).get("state")
    
    # 1. PRIORITY: REAL JOURNALISM (If a professional recap exists)
    for art in data.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # 2. DYNAMIC RECAP (POST-GAME)
    if state == "post":
        comp = header.get("competitors", [])
        winner = next((t for t in comp if t.get("winner")), comp[0])
        loser = next((t for t in comp if not t.get("winner")), comp[1])
        
        w_score, l_score = int(winner['score']), int(loser['score'])
        margin = w_score - l_score
        
        # Determine Narrative Vibe
        if margin > 20: tone = "completely dismantled"
        elif margin < 5: tone = "clawed out a gritty win over"
        else: tone = "took care of business against"

        # Search for a Star Player
        hero_line = ""
        for cat in data.get("leaders", []):
            if cat.get("name") in ["points", "goals", "runs", "passingYards"]:
                top = cat["leaders"][0]
                hero_line = f" {top['athlete']['displayName']} was the catalyst, providing {top['displayValue']} to keep the lead safe."
                break

        return f"**{winner['team']['location'].upper()}** — The {winner['team']['displayName']} {tone} the {loser['team']['displayName']} today, finishing {w_score}-{l_score}.{hero_line} Standard league review is complete, and the wire is now closed for this contest."

    # 3. DYNAMIC PREVIEW (UPCOMING)
    else:
        venue = data.get("gameInfo", {}).get("venue", {}).get("fullName", "local grounds")
        odds = data.get("pickcenter", [{}])[0].get("details", "a toss-up")
        return f"**STADIUM WIRE** — The {away} are set to challenge the {home} at {venue}. Early betting lines suggest this one is {odds}. Both squads have arrived on-site, and the atmosphere is building for a pivotal clash."

def get_cricket_wc(whitelist):
    """Hits the CricAPI endpoints for the ongoing T20 World Cup."""
    games = []
    urls = [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
            f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]
    for url in urls:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                if is_match(m.get("name", ""), whitelist):
                    # Logic for Cricket Score strings (e.g. '120/4 vs 110/10')
                    status = m.get("status", "Match Live")
                    games.append({
                        "id": m['id'],
                        "sport": "T20 WORLD CUP",
                        "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": m.get("t2", "TBD"), "logo": m.get("t2Img", ""), "score": m.get("t2s", "0/0")},
                        "away": {"name": m.get("t1", "TBD"), "logo": m.get("t1Img", ""), "score": m.get("t1s", "0/0")},
                        "story": f"**PITCH-SIDE** — {status}. The ICC reports a high-intensity environment as {m.get('t1')} and {m.get('t2')} square off in group play. Wire analysis to follow.",
                        "raw_date": m.get("dateTimeGMT") or m.get("date")
                    })
        except: continue
    return games

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    games = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                # Fetch detailed summary for the 'Human' story
                summary = requests.get(f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event['id']}").json()
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
    # This renders the sleek, dark-mode 'Tempe Torch' interface
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
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 40px; display: flex; justify-content: space-between; }}
            #live-clock {{ font-family: monospace; font-size: 1.2rem; color: var(--accent); }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .card-header {{ background: #1a1a1a; padding: 10px; font-size: 0.7rem; font-weight: 900; display: flex; justify-content: space-between; }}
            .score-area {{ display: flex; justify-content: space-around; padding: 25px; text-align: center; }}
            .logo {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 10px; }}
            .score {{ font-size: 2rem; font-weight: 900; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 100; justify-content: center; align-items: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 40px; border-radius: 4px; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock"></div></header>
    <div class="grid" id="main-grid"></div>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="border-bottom: 4px solid #111; padding-bottom: 10px; text-transform: uppercase;"></h2>
        <div id="modal-body" style="font-family: 'Georgia', serif; font-size: 1.2rem; line-height: 1.7;"></div>
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
                    <div style="opacity:0.2">VS</div>
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
    
    # Standard Leagues
    for s, l in [("basketball", "nba"), ("hockey", "nhl"), ("basketball", "mens-college-basketball")]:
        all_games.extend(get_espn_data(s, l, whitelist))
    
    # Cricket World Cup (CricAPI)
    all_games.extend(get_cricket_wc(whitelist))
    
    # Sort: Live first, then by date
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
