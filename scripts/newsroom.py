import requests
import json
from datetime import datetime, timedelta
import pytz
import os
import re

# --- CONFIG ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
CRICKET_API_KEY = os.getenv("CRICKET_API_KEY", "52613cff-3da7-45f7-9793-a863aad4fb86")

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return [l.strip().lower() for l in f if l.strip()]
    return ["india", "namibia", "clippers", "suns", "asu"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    return any(re.search(r'\b' + re.escape(w) + r'\b', text_clean) for w in whitelist)

def craft_ap_story(data, home, away):
    """The AP Journalism Engine: Mimics professional sports wire recaps."""
    header = data.get("header", {}).get("competitions", [{}])[0]
    state = header.get("status", {}).get("type", {}).get("state")
    
    # Priority 1: Use actual ESPN Recap if it exists (Professional standard)
    for art in data.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # Priority 2: Generative AP Recap (Post-Game)
    if state == "post":
        comp = header.get("competitors", [])
        winner = next((t for t in comp if t.get("winner")), comp[0])
        loser = next((t for t in comp if not t.get("winner")), comp[1])
        w_score, l_score = int(winner.get('score', 0)), int(loser.get('score', 0))
        location = winner.get('team', {}).get('location', '').upper()
        
        # Determine the Lead Verb
        diff = w_score - l_score
        if diff > 20: verb = "cruised to a dominant victory"
        elif diff < 5: verb = "held off a late rally"
        else: verb = "pulled away in the second half"

        # Find High Scorer
        hero_text = ""
        for cat in data.get("leaders", []):
            if cat.get("name") in ["points", "goals", "runs"]:
                top = cat["leaders"][0]
                name = top['athlete']['displayName']
                val = top['displayValue']
                hero_text = f"{name} led the charge with {val}, helping the {winner['team']['displayName']} stay aggressive throughout."
                break

        return f"**{location}** — The {winner['team']['displayName']} {verb} to defeat the {loser['team']['displayName']} {w_score}-{l_score} on Friday night. {hero_text} Despite a gritty effort from the {loser['team']['displayName']}, they were unable to overcome a double-digit deficit in the final period."

    # Priority 3: AP Preview
    venue = data.get("gameInfo", {}).get("venue", {}).get("fullName", "the arena")
    return f"**PREVIEW** — The {away} travel to face the {home} at {venue}. Wire reports indicate a capacity crowd is expected as both squads look to gain momentum in the standings."

def get_cricket_wc(whitelist):
    """STRICT: T20 World Cup, Whitelisted Teams, and 4-Day Date Window."""
    games = []
    # Phoenix Time Logic for Filtering
    az_tz = pytz.timezone('America/Phoenix')
    today = datetime.now(az_tz)
    start_window = today - timedelta(days=2)
    end_window = today + timedelta(days=2)

    urls = [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
            f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]
    
    seen_ids = set()
    for url in urls:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                if m['id'] in seen_ids: continue
                
                # 1. DATE FILTER (T20 format often provides dateTimeGMT)
                dt_str = m.get("dateTimeGMT") or m.get("date")
                try:
                    m_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).astimezone(az_tz)
                    if not (start_window <= m_date <= end_window): continue
                except: continue

                t_info = m.get("teamInfo", [])
                t1 = t_info[0] if len(t_info) > 0 else {"name": m.get("t1", ""), "img": ""}
                t2 = t_info[1] if len(t_info) > 1 else {"name": m.get("t2", ""), "img": ""}
                
                # 2. SERIES & WHITELIST FILTER
                is_wc = "world cup" in m.get("name", "").lower() or "t20" in m.get("name", "").lower()
                if is_wc and (is_match(t1['name'], whitelist) or is_match(t2['name'], whitelist)):
                    seen_ids.add(m['id'])
                    status = m.get("status", "Live")
                    games.append({
                        "id": m['id'], "sport": "T20 WORLD CUP", "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": t2['name'], "logo": t2.get('img', ""), "score": m.get("t2s", "0/0")},
                        "away": {"name": t1['name'], "logo": t1.get('img', ""), "score": m.get("t1s", "0/0")},
                        "story": f"**PITCH DISPATCH** — {status}. Match officials report high-intensity group play at the T20 World Cup. {t1['name']} and {t2['name']} continue to battle for pivotal points.",
                        "raw_date": dt_str
                    })
        except: continue
    return games

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
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
                    "id": event['id'], "sport": league.upper().replace("-", " "), "status": event["status"]["type"]["state"],
                    "home": {"name": home['team']['displayName'], "logo": home['team'].get("logo", ""), "score": home.get("score", "0")},
                    "away": {"name": away['team']['displayName'], "logo": away['team'].get("logo", ""), "score": away.get("score", "0")},
                    "story": craft_ap_story(summary, home['team']['displayName'], away['team']['displayName']),
                    "raw_date": event.get("date")
                })
        return games
    except: return []

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now = datetime.now(az_tz).strftime("%m/%d/%Y %H:%M:%S")
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
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .score-area {{ display: flex; justify-content: space-around; padding: 25px; text-align: center; align-items: center; }}
            .logo {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 8px; background: #fff; border-radius: 50%; padding: 4px; }}
            .score {{ font-size: 2.2rem; font-weight: 900; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; border-top: 1px solid #333; }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 50px; border-radius: 2px; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock"></div></header>
    <div class="grid" id="main-grid"></div>
    <footer style="margin-top:40px; text-align:center; color:#555; font-size:0.8rem;">LAST WIRE UPDATE: {now} AZT</footer>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="border-bottom: 4px solid #111; padding-bottom:10px; text-transform:uppercase;"></h2>
        <div id="modal-body" style="font-family: 'Georgia', serif; font-size: 1.3rem; line-height: 1.8; margin-top: 20px;"></div>
    </div></div>
    <script>
        const games = {games_json};
        function updateClock() {{
            document.getElementById('live-clock').innerText = new Date().toLocaleString('en-US', {{ timeZone: 'America/Phoenix', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }}) + " AZT";
        }}
        setInterval(updateClock, 1000); updateClock();

        const grid = document.getElementById('main-grid');
        games.forEach(g => {{
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `<div style="background:#1a1a1a; padding:10px; font-size:0.7rem; font-weight:900;">${{g.sport}} | ${{g.status.toUpperCase()}}</div>
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
    
    leagues = [
        ("basketball", "nba"), ("basketball", "wnba"),
        ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("hockey", "nhl"), ("hockey", "mens-college-hockey"),
        ("football", "nfl"), ("football", "college-football"),
        ("baseball", "mlb"), ("soccer", "usa.1")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist))
    
    all_games.extend(get_cricket_wc(whitelist))
    
    # Sort: Live first, then newest
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
