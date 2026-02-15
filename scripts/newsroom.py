import requests
import json
from datetime import datetime
import pytz
import os
import re
import time

# --- CONFIG ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"

def load_whitelist():
    """Loads teams from file or defaults to the core Arizona/whitelist beat."""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return [l.strip().lower() for l in f if l.strip()]
    return ["suns", "asu", "arizona state", "jazz", "kings", "maple leafs", "devils", "diamondbacks"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    return any(re.search(r'\b' + re.escape(w) + r'\b', text_clean) for w in whitelist)

def craft_ap_story(summary_json):
    """Deep Data Miner: Extracts professional story beats from ESPN JSON."""
    header = summary_json.get("header", {})
    comp = header.get("competitions", [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state")
    teams = comp.get("competitors", [])
    
    # Priority 1: Check if ESPN has a professional recap written already
    for art in summary_json.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # Priority 2: Generate an AP-style dispatch if the game is finished
    if state == "post":
        winner = next((t for t in teams if t.get("winner")), teams[0])
        loser = next((t for t in teams if not t.get("winner")), teams[1])
        w_t, l_t = winner['team'], loser['team']
        
        dateline = f"**{w_t['location'].upper()}** — "
        lead = f"The {w_t['displayName']} claimed a decisive victory, defeating the {l_t['displayName']} {winner['score']}-{loser['score']}."
        
        w_rec = winner.get('records', [{}])[0].get('summary', '0-0')
        standing = f"\n\nThe win moves the {w_t['shortDisplayName']} to {w_rec} on the season."
        
        up = summary_json.get("schedule", {}).get("upcoming", [])
        next_match = f"\n\n**UP NEXT:** {w_t['shortDisplayName']} continues their schedule against {up[0]['shortName'] if up else 'their next conference opponent'}."
        
        return f"{dateline}{lead}{standing}{next_match}"

    return "DISPATCH — Pre-game rituals are underway. Lineup adjustments and local conditions are being monitored for tonight's start."

def get_espn_data(sport, league, whitelist, seen_ids):
    """Fetches data using 'groups' to unlock non-ranked college teams (like ASU)."""
    base_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    
    # Critical: '50' is the magic ID to see ALL college teams, not just Top 25
    group_id = "50" if "college-" in league else "80"
    
    params = {
        "limit": "250",   # High limit for busy college Saturdays
        "groups": group_id, 
        "cb": int(time.time()) 
    }
    
    games = []
    try:
        data = requests.get(base_url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = str(event['id'])
            if eid in seen_ids: continue
            
            # Match against whitelist (e.g., 'ASU' vs 'Arizona State')
            if is_match(event.get("name", ""), whitelist):
                sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}&cb={int(time.time())}"
                summary = requests.get(sum_url).json()
                comp = event["competitions"][0]
                home, away = comp['competitors'][0], comp['competitors'][1]
                
                seen_ids.add(eid)
                games.append({
                    "id": eid, 
                    "sport": league.upper().replace("-", " "), 
                    "status": event["status"]["type"]["state"],
                    "home": {"name": home['team']['displayName'], "score": home.get("score", "0")},
                    "away": {"name": away['team']['displayName'], "score": away.get("score", "0")},
                    "story": craft_ap_story(summary),
                    "raw_date": event.get("date")
                })
    except:
        pass
    return games

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now = datetime.now(az_tz).strftime("%B %d, %Y")
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>The Tempe Torch | Sports Wire</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@900&family=Inter:wght@400;700&family=Georgia&display=swap">
        <style>
            :root {{ --bg: #fdfdfd; --text: #111; --accent: #a00; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }}
            header {{ text-align: center; border-bottom: 5px double #000; padding-bottom: 20px; margin-bottom: 40px; }}
            h1 {{ font-family: 'Playfair Display', serif; font-size: 4rem; margin: 0; text-transform: uppercase; }}
            .date-bar {{ border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 5px; font-weight: bold; display: flex; justify-content: space-between; margin-top: 10px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
            .card {{ border: 1px solid #ccc; padding: 25px; background: #fff; cursor: pointer; transition: 0.2s; }}
            .card:hover {{ border-color: #000; box-shadow: 6px 6px 0px #eee; }}
            .sport-label {{ font-size: 0.75rem; font-weight: 900; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; }}
            .matchup-text {{ font-weight: 700; font-size: 1.1rem; margin-top: 10px; line-height: 1.2; }}
            .score-display {{ font-family: 'Playfair Display', serif; font-size: 2.8rem; margin: 15px 0; }}
            
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: white; z-index: 1000; overflow-y: auto; }}
            .modal-content {{ max-width: 750px; margin: 60px auto; padding: 30px; border: 1px solid #eee; }}
            .story-body {{ font-family: 'Georgia', serif; font-size: 1.35rem; line-height: 1.8; white-space: pre-line; color: #333; }}
            .close-btn {{ background: #000; color: #fff; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
    <header>
        <h1>The Tempe Torch</h1>
        <div class="date-bar"><span>{now}</span><span id="clock"></span></div>
    </header>
    <div class="grid" id="main-grid"></div>

    <div id="modal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeModal()">BACK TO WIRE</button>
            <div id="modal-sport" class="sport-label"></div>
            <h2 id="modal-title" style="font-family:'Playfair Display'; font-size: 3rem; margin: 10px 0;"></h2>
            <hr>
            <div id="modal-body" class="story-body"></div>
        </div>
    </div>

    <script>
        const games = {games_json};
        function tick() {{ document.getElementById('clock').innerText = new Date().toLocaleTimeString('en-US', {{hour12:false}}) + " AZT"; }}
        setInterval(tick, 1000); tick();

        const grid = document.getElementById('main-grid');
        if(games.length === 0) {{
            grid.innerHTML = "<p>The newsroom is quiet. Check back shortly for whitelist updates.</p>";
        }}

        games.forEach(g => {{
            const div = document.createElement('div');
            div.className = 'card';
            div.onclick = () => openModal(g.id);
            const statusStr = g.status === 'in' ? '<span style="color:red">● LIVE</span>' : g.status.toUpperCase();
            div.innerHTML = `
                <span class="sport-label">${{g.sport}} // ${{statusStr}}</span>
                <div class="matchup-text">${{g.away.name}}<br>at ${{g.home.name}}</div>
                <div class="score-display">${{g.away.score}} — ${{g.home.score}}</div>
            `;
            grid.appendChild(div);
        }});

        function openModal(id) {{
            const g = games.find(x => x.id === id);
            document.getElementById('modal-title').innerText = g.away.name + " at " + g.home.name;
            document.getElementById('modal-sport').innerText = g.sport;
            document.getElementById('modal-body').innerHTML = g.story;
            document.getElementById('modal').style.display = 'block';
            document.body.style.overflow = 'hidden';
        }}
        function closeModal() {{ 
            document.getElementById('modal').style.display = 'none'; 
            document.body.style.overflow = 'auto';
        }}
    </script>
    </body></html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    seen = set()
    
    # Correct league mappings including "buried" Softball
    leagues = [
        ("basketball", "nba"),
        ("basketball", "mens-college-basketball"),
        ("hockey", "nhl"),
        ("hockey", "mens-college-hockey"),
        ("baseball", "mlb"),
        ("baseball", "college-baseball"),
        ("baseball", "college-softball") 
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    # Sort: Live/Recent games first
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
