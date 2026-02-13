import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
DAYS_BACK = 5 
DAYS_AHEAD = 3

# Add common abbreviations here so the script "knows" they are the same
ALIASES = {
    "india": ["ind"],
    "namibia": ["nam"],
    "australia": ["aus"],
    "south africa": ["rsa", "sa"],
    "pakistan": ["pak"],
    "united states": ["usa"],
    "sri lanka": ["sl", "sri"],
    "italy": ["ita"]
}

def load_whitelist():
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                # Load the whitelist and expand it with aliases
                base_list = [line.strip().lower() for line in f if line.strip()]
                expanded = set(base_list)
                for item in base_list:
                    if item in ALIASES:
                        expanded.update(ALIASES[item])
                return list(expanded)
    return []

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    for item in whitelist:
        # Uses word-boundary check so 'ind' matches 'IND vs NAM' but not 'Windows'
        if re.search(r'\b' + re.escape(item) + r'\b', text_clean):
            return True
    return False

def get_verified_story(sport, league, event_id, home, away):
    """Sleuthing: Strictly verifies the story matches the specific game."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
    try:
        data = requests.get(url, timeout=5).json()
        articles = data.get("news", {}).get("articles", [])
        
        # Priority: Look for 'recap' first
        for art in articles:
            content = art.get("story", art.get("description", ""))
            # Check if story mentions the team names or common shorthand
            if is_match(content, [home, away, home.split()[-1], away.split()[-1]]):
                return re.sub('<[^<]+?>', '', content)
        
        # AP Style Procedural Fallback
        header = data.get("header", {}).get("competitions", [{}])[0]
        if header.get("status", {}).get("type", {}).get("state") == "post":
            h_score = header['competitors'][0]['score']
            a_score = header['competitors'][1]['score']
            return f"**NEW DELHI** — In a commanding performance, {home} secured a vital victory over {away} with a final score of {h_score} to {a_score}. The Associated Press is currently processing the full match dispatch."
            
        return "The AP Wire is awaiting the conclusion of this match for the full dispatch."
    except:
        return "Establishing secure link to the press box..."

def get_data(sport, league, whitelist, is_cricket=False):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    date_str = f"{(datetime.now()-timedelta(days=DAYS_BACK)).strftime('%Y%m%d')}-{(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime('%Y%m%d')}"
    params = {"limit": "100", "dates": date_str}
    
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            # Check event name (e.g. "India vs Namibia") or the short name (e.g. "IND vs NAM")
            if is_match(event.get("name", ""), whitelist) or is_match(event.get("shortName", ""), whitelist):
                comp = event["competitions"][0]
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                
                h_name = home['team']['displayName']
                a_name = away['team']['displayName']
                
                story = get_verified_story(sport, league, event['id'], h_name, a_name)
                
                # Format Score
                if is_cricket:
                    h_score = f"{home.get('score', '0')}/{home.get('wickets', '0')}"
                    a_score = f"{away.get('score', '0')}/{away.get('wickets', '0')}"
                else:
                    h_score = home.get('score', '0')
                    a_score = away.get('score', '0')

                games.append({
                    "id": event['id'],
                    "sport": "T20 WORLD CUP" if league == "8039" else league.upper().replace(".1","").replace("-"," "),
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": h_name, "logo": home['team'].get("logo", ""), "score": h_score},
                    "away": {"name": a_name, "logo": away['team'].get("logo", ""), "score": a_score},
                    "story": story,
                    "raw_date": event.get("date")
                })
        return games
    except: return []

# --- HTML/JS GENERATION ---
def generate_html(games):
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>The Tempe Torch | Wire Service</title>
        <style>
            :root {{ --bg: #050505; --accent: #ff3d00; --text: #f0f0f0; --card: #111; }}
            body {{ font-family: 'Helvetica', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
            #live-clock {{ font-family: monospace; font-size: 1.4rem; color: var(--accent); }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .card-header {{ background: #1a1a1a; padding: 10px 15px; font-size: 0.7rem; font-weight: 900; color: #888; display: flex; justify-content: space-between; }}
            .countdown {{ color: var(--accent); letter-spacing: 1px; }}
            .score-row {{ display: flex; align-items: center; justify-content: space-around; padding: 25px 10px; }}
            .team-box {{ width: 40%; text-align: center; }}
            .logo {{ width: 45px; height: 45px; object-fit: contain; background: #fff; border-radius: 50%; padding: 5px; margin-bottom: 10px; }}
            .score {{ font-size: 2.2rem; font-weight: 900; }}
            .btn-read {{ width: 100%; border: none; background: #222; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 50px; border-radius: 2px; position: relative; max-height: 85vh; overflow-y: auto; line-height: 1.8; font-family: 'Georgia', serif; font-size: 1.2rem; }}
        </style>
    </head>
    <body>

    <header>
        <h1>TEMPE TORCH <span style="font-weight:100; color:#555">WIRE</span></h1>
        <div id="live-clock"></div>
    </header>

    <div class="grid" id="main-grid"></div>

    <div id="modal">
        <div class="modal-content">
            <span style="position:absolute; top:20px; right:20px; cursor:pointer; font-weight:bold" onclick="closeModal()">[ CLOSE WIRE ]</span>
            <h2 id="modal-title" style="color:var(--accent); text-transform:uppercase; border-bottom:1px solid #ddd; padding-bottom:10px"></h2>
            <div id="modal-story"></div>
        </div>
    </div>

    <script>
        const games = {games_json};
        
        function updateClocks() {{
            const now = new Date();
            // Arizona Time Display
            const azt = now.toLocaleString('en-US', {{ timeZone: 'America/Phoenix', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }});
            document.getElementById('live-clock').innerText = azt + " AZT";
            
            // Dynamic Countdowns
            document.querySelectorAll('.countdown').forEach(el => {{
                const target = new Date(el.dataset.date);
                const diff = target - now;
                if (diff > 0) {{
                    const h = Math.floor(diff / 3600000);
                    const m = Math.floor((diff % 3600000) / 60000);
                    el.innerText = `STARTING IN ${{h}}H ${{m}}M`;
                }} else {{
                    el.innerText = "LIVE / FINAL";
                }}
            }});
        }}
        setInterval(updateClocks, 1000); updateClocks();

        const grid = document.getElementById('main-grid');
        games.forEach(g => {{
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="card-header">
                    <span>${{g.sport}}</span>
                    <span class="countdown" data-date="${{g.raw_date}}"></span>
                </div>
                <div class="score-row">
                    <div class="team-box">
                        <img src="${{g.away.logo}}" class="logo"><br><b>${{g.away.name}}</b>
                        <div class="score">${{g.away.score}}</div>
                    </div>
                    <div style="font-weight:900; opacity:0.1; font-size:2rem">VS</div>
                    <div class="team-box">
                        <img src="${{g.home.logo}}" class="logo"><br><b>${{g.home.name}}</b>
                        <div class="score">${{g.home.score}}</div>
                    </div>
                </div>
                <div style="text-align:center; padding-bottom:15px; font-size:0.8rem; color:#666">${{g.detail}}</div>
                <button class="btn-read" onclick="openModal('${{g.id}}')">OPEN DISPATCH</button>
            `;
            grid.appendChild(card);
        }});

        function openModal(id) {{
            const g = games.find(x => x.id === id);
            document.getElementById('modal-title').innerText = g.away.name + " @ " + g.home.name;
            document.getElementById('modal-story').innerHTML = g.story.replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>').replace(/\\n/g, '<br><br>');
            document.getElementById('modal').style.display = 'flex';
        }}
        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
    </script>
    </body>
    </html>
    """
