import requests
import json
from datetime import datetime, timedelta
import pytz
import os
import re

# --- CONFIG ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"
CRICKET_API_KEY = os.getenv("CRICKET_API_KEY", "52613cff-3da7-45f7-9793-a863aad4fb86")

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return [l.strip().lower() for l in f if l.strip()]
    return ["india", "namibia", "suns", "asu", "duke", "clemson"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    return any(re.search(r'\b' + re.escape(w) + r'\b', text_clean) for w in whitelist)

def craft_ap_story(data, home_name, away_name):
    """The AP Journalism Engine: Mimics specific wire recap structures."""
    header = data.get("header", {}).get("competitions", [{}])[0]
    state = header.get("status", {}).get("type", {}).get("state")
    
    # 1. PRIORITY: REAL RECAPS
    for art in data.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    # 2. GENERATIVE AP WIRE (The "Duke Template")
    if state == "post":
        comp = header.get("competitors", [])
        winner = next((t for t in comp if t.get("winner")), comp[0])
        loser = next((t for t in comp if not t.get("winner")), comp[1])
        w_name = winner['team']['displayName']
        l_name = loser['team']['displayName']
        w_score = winner.get('score', '0')
        l_score = loser.get('score', '0')
        loc = winner['team'].get('location', '').upper()
        
        # Stat Extraction
        hero_line = ""
        team_stats = ""
        for cat in data.get("leaders", []):
            if cat.get("name") in ["points", "goals", "runs"]:
                top = cat["leaders"][0]
                hero_line = f"{top['athlete']['displayName']} had {top['displayValue']} to lead the {w_name}."
                break
        
        # Record & Context
        w_rec = winner.get('records', [{}])[0].get('summary', '')
        l_rec = loser.get('records', [{}])[0].get('summary', '')
        
        # The Lead (Inverted Pyramid)
        story = f"{loc} — {hero_line} {w_name} ({w_rec}) defeated {l_name} ({l_rec}) {w_score}-{l_score} on Friday night."
        
        # The Detail Paragraph
        story += f"\n\nThe {w_name} capitalized on efficient scoring opportunities after the break, extending a narrow margin into a comfortable lead midway through the final period. The result marks a key milestone in the {w_name} season as they look toward the postseason rankings."
        
        # The "Up Next" Segment
        story += f"\n\n**Up next**\n{l_name}: Next contest scheduled for Wednesday.\n{w_name}: Returns home for a matchup on Monday."
        
        return story

    # 3. AP PREVIEW
    venue = data.get("gameInfo", {}).get("venue", {}).get("fullName", "the arena")
    return f"**PREVIEW** — The {away_name} visit the {home_name} at {venue}. Tip-off is set as both teams jockey for position in the conference standings."

def get_cricket_wc(whitelist):
    """T20 World Cup, Whitelisted Teams, 4-Day Window."""
    games = []
    az_tz = pytz.timezone('America/Phoenix')
    today = datetime.now(az_tz)
    
    urls = [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
            f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]
    
    seen_ids = set()
    for url in urls:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                if m['id'] in seen_ids: continue
                
                # Date logic
                dt_str = m.get("dateTimeGMT") or m.get("date")
                try:
                    m_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).astimezone(az_tz)
                    if abs((m_date - today).days) > 2: continue
                except: continue

                t_info = m.get("teamInfo", [])
                t1 = t_info[0] if len(t_info) > 0 else {"name": m.get("t1", ""), "img": ""}
                t2 = t_info[1] if len(t_info) > 1 else {"name": m.get("t2", ""), "img": ""}
                
                is_wc = "world cup" in m.get("name", "").lower() or "t20" in m.get("name", "").lower()
                if is_wc and (is_match(t1['name'], whitelist) or is_match(t2['name'], whitelist)):
                    seen_ids.add(m['id'])
                    games.append({
                        "id": m['id'], "sport": "T20 WORLD CUP", "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": t2['name'], "logo": t2.get('img', ""), "score": m.get("t2s", "0/0")},
                        "away": {"name": t1['name'], "logo": t1.get('img', ""), "score": m.get("t1s", "0/0")},
                        "story": f"**WIRE REPORT** — {m.get('status')}. The T20 World Cup continues as {t1['name']} and {t2['name']} meet in a pivotal group stage matchup.",
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
                # Summary endpoint for the detailed stats
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
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;900&family=Georgia&display=swap">
        <style>
            :root {{ --bg: #050505; --accent: #ff3d00; --card: #121212; --text: #eee; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
            .score-area {{ display: flex; justify-content: space-around; padding: 25px; text-align: center; align-items: center; border-bottom: 1px solid #222; }}
            .logo {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 8px; background: #fff; border-radius: 50%; padding: 4px; }}
            .score {{ font-size: 2.2rem; font-weight: 900; }}
            .btn-read {{ width: 100%; border: none; background: #1a1a1a; color: #fff; padding: 15px; cursor: pointer; font-weight: bold; transition: 0.2s; }}
            .btn-read:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 850px; width: 95%; padding: 60px; border-radius: 2px; overflow-y: auto; max-height: 90vh; }}
            .modal-content h2 {{ font-weight: 900; text-transform: uppercase; border-bottom: 5px solid #111; padding-bottom: 15px; }}
            .story-body {{ font-family: 'Georgia', serif; font-size: 1.4rem; line-height: 1.7; white-space: pre-line; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock"></div></header>
    <div class="grid" id="main-grid"></div>
    <footer style="margin-top:40px; text-align:center; color:#555; font-size:0.8rem;">LAST WIRE UPDATE: {now} AZT</footer>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title"></h2>
        <div id="modal-body" class="story-body"></div>
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
    
    # Final sorting: Live games on top, then by date.
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
