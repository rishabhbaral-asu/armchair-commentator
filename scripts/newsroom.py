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
    return ["india", "namibia", "suns", "asu", "jazz", "kings", "maple leafs"]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    return any(re.search(r'\b' + re.escape(w) + r'\b', text_clean) for w in whitelist)

def get_stat(stats, label):
    """Helper to pull specific metrics from ESPN's deep JSON."""
    for s in stats:
        if s.get('name') == label:
            return s.get('displayValue', '0')
    return "0"

def craft_ap_story(summary_json):
    """The Data-Journalist Engine: Builds stories from raw percentages and trends."""
    header = summary_json.get("header", {})
    comp = header.get("competitions", [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state")
    teams = comp.get("competitors", [])
    
    # Priority: Professional Recap
    for art in summary_json.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    if state == "post":
        winner = next((t for t in teams if t.get("winner")), teams[0])
        loser = next((t for t in teams if not t.get("winner")), teams[1])
        
        w_team = winner['team']
        l_team = loser['team']
        w_score, l_score = int(winner['score']), int(loser['score'])
        
        # Deep Data Mining
        box = summary_json.get("boxscore", {}).get("teams", [])
        w_stats = box[0].get('statistics', []) if box and box[0]['team']['id'] == w_team['id'] else box[1].get('statistics', []) if len(box)>1 else []
        
        fg_pct = get_stat(w_stats, 'fieldGoalsPercentage')
        three_pct = get_stat(w_stats, 'threePointFieldGoalsPercentage')
        rebounds = get_stat(w_stats, 'totalRebounds')
        
        # Leader Hunt
        leaders = summary_json.get("leaders", [])
        top_performer = "The winning effort"
        if leaders:
            top = leaders[0]['leaders'][0]
            top_performer = f"{top['athlete']['displayName']}, who finished with {top['displayValue']} {leaders[0]['name']}"

        # AP Inverted Pyramid Construction
        dateline = f"**{w_team['location'].upper()}** — "
        lead = f"{top_performer} led the {w_team['displayName']} past the {l_team['displayName']} {w_score}-{l_score} on Friday night."
        
        # Adding Contextual Meat
        stats_para = f"The {w_team['shortDisplayName']} shot {fg_pct}% from the floor and connected on {three_pct}% of their looks from deep. On the glass, they out-muscled {l_team['shortDisplayName']}, pulling down {rebounds} total rebounds to control the tempo."
        
        standing = ""
        if 'records' in winner:
            standing = f"The victory moves {w_team['shortDisplayName']} to {winner['records'][0]['summary']} on the season."

        # Up Next
        upcoming = summary_json.get("schedule", {}).get("upcoming", [])
        up_next = "\n\n**Up next**\n"
        if upcoming:
            up_next += f"{w_team['shortDisplayName']}: {upcoming[0].get('shortName', 'Next Matchup')}"
        else:
            up_next += f"{w_team['shortDisplayName']}: Scheduled for next week."

        return f"{dateline}{lead}\n\n{stats_para} {standing}{up_next}"

    return "STADIUM DISPATCH — Teams are currently warming up. Scouting reports suggest a high-tempo offensive approach for both squads."

def get_cricket_wc(whitelist):
    games = []
    az_tz = pytz.timezone('America/Phoenix')
    today = datetime.now(az_tz)
    
    # 52613cff-3da7-45f7-9793-a863aad4fb86
    urls = [f"https://api.cricapi.com/v1/cricScore?apikey={CRICKET_API_KEY}",
            f"https://api.cricapi.com/v1/matches?apikey={CRICKET_API_KEY}&offset=0"]
    
    seen_ids = set()
    for url in urls:
        try:
            res = requests.get(url, timeout=10).json().get("data", [])
            for m in res:
                m_id = str(m['id'])
                if m_id in seen_ids: continue
                
                # STRICT 2-DAY WINDOW
                dt_str = m.get("dateTimeGMT") or m.get("date")
                try:
                    m_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).astimezone(az_tz)
                    if abs((m_date - today).days) > 1: continue 
                except: continue

                t_info = m.get("teamInfo", [])
                t1 = t_info[0] if len(t_info) > 0 else {"name": m.get("t1", ""), "img": ""}
                t2 = t_info[1] if len(t_info) > 1 else {"name": m.get("t2", ""), "img": ""}
                
                if (is_match(t1['name'], whitelist) or is_match(t2['name'], whitelist)):
                    seen_ids.add(m_id)
                    games.append({
                        "id": m_id, "sport": "T20 WORLD CUP", "status": "post" if m.get("matchEnded") else "in",
                        "home": {"name": t2['name'], "logo": t2.get('img', ""), "score": m.get("t2s", "0/0")},
                        "away": {"name": t1['name'], "logo": t1.get('img', ""), "score": m.get("t1s", "0/0")},
                        "story": f"**WIRE DISPATCH** — {m.get('status')}. Reporting from the T20 World Cup group stage. {t1['name']} and {t2['name']} are locked in a high-stakes fixture affecting tournament progression.",
                        "raw_date": dt_str
                    })
        except: continue
    return games

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"dates": "20260211-20260215", "limit": "100"}
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            e_id = str(event['id'])
            if e_id in seen_ids: continue
            
            if is_match(event.get("name", ""), whitelist):
                sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={e_id}"
                summary = requests.get(sum_url).json()
                comp = event["competitions"][0]
                home, away = comp['competitors'][0], comp['competitors'][1]
                
                seen_ids.add(e_id)
                games.append({
                    "id": e_id, "sport": league.upper().replace("-", " "), "status": event["status"]["type"]["state"],
                    "home": {"name": home['team']['displayName'], "logo": home['team'].get("logo", ""), "score": home.get("score", "0")},
                    "away": {"name": away['team']['displayName'], "logo": away['team'].get("logo", ""), "score": away.get("score", "0")},
                    "story": craft_ap_story(summary),
                    "raw_date": event.get("date")
                })
        return games
    except: return []

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now = datetime.now(az_tz).strftime("%B %d, %Y - %I:%M %p")
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>Tempe Torch | Wire Service</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;900&family=Georgia&display=swap">
        <style>
            :root {{ --bg: #0a0a0a; --accent: #ff3d00; --card: #151515; --text: #f0f0f0; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }}
            header {{ border-bottom: 3px solid var(--accent); padding-bottom: 20px; margin-bottom: 50px; display: flex; justify-content: space-between; align-items: flex-end; }}
            h1 {{ font-size: 3rem; margin: 0; font-weight: 900; letter-spacing: -2px; }}
            h1 span {{ color: #444; font-weight: 400; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 30px; }}
            .card {{ background: var(--card); border: 1px solid #333; transition: 0.3s; }}
            .card:hover {{ border-color: var(--accent); }}
            .card-meta {{ background: #222; padding: 10px 20px; font-size: 0.75rem; font-weight: 900; letter-spacing: 1px; color: #aaa; }}
            .score-box {{ display: flex; justify-content: space-between; align-items: center; padding: 30px; }}
            .team {{ text-align: center; width: 40%; }}
            .team img {{ width: 60px; height: 60px; background: #fff; border-radius: 50%; padding: 5px; margin-bottom: 10px; }}
            .score {{ font-size: 3rem; font-weight: 900; color: #fff; }}
            .btn-dispatch {{ width: 100%; border: none; background: #222; color: #fff; padding: 18px; cursor: pointer; font-weight: 900; border-top: 1px solid #333; }}
            .btn-dispatch:hover {{ background: var(--accent); }}
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; align-items: center; justify-content: center; }}
            .modal-content {{ background: #fff; color: #111; max-width: 800px; width: 90%; padding: 60px; box-shadow: 0 0 50px rgba(255,61,0,0.2); }}
            .story-text {{ font-family: 'Georgia', serif; font-size: 1.4rem; line-height: 1.8; white-space: pre-line; }}
        </style>
    </head>
    <body>
    <header><h1>TEMPE TORCH <span>WIRE</span></h1><div id="live-clock">--:--</div></header>
    <div class="grid" id="main-grid"></div>
    <footer style="margin-top:80px; text-align:center; color:#444; font-weight:900; text-transform:uppercase;">Last Dispatch: {now} AZT</footer>
    <div id="modal" onclick="closeModal()"><div class="modal-content" onclick="event.stopPropagation()">
        <h2 id="modal-title" style="font-size: 2.5rem; margin-top:0; border-bottom: 8px solid #111; padding-bottom:15px;"></h2>
        <div id="modal-body" class="story-text"></div>
    </div></div>
    <script>
        const games = {games_json};
        function updateClock() {{
            document.getElementById('live-clock').innerText = new Date().toLocaleTimeString('en-US', {{ timeZone: 'America/Phoenix', hour12: false }}) + " AZT";
        }}
        setInterval(updateClock, 1000); updateClock();
        const grid = document.getElementById('main-grid');
        games.forEach(g => {{
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `<div class="card-meta">${{g.sport}} // ${{g.status.toUpperCase()}}</div>
                <div class="score-box">
                    <div class="team"><img src="${{g.away.logo}}" onerror="this.src='https://ui-avatars.com/api/?name=${{g.away.name}}'"><br><b>${{g.away.name}}</b></div>
                    <div class="score">${{g.away.score}} - ${{g.home.score}}</div>
                    <div class="team"><img src="${{g.home.logo}}" onerror="this.src='https://ui-avatars.com/api/?name=${{g.home.name}}'"><br><b>${{g.home.name}}</b></div>
                </div>
                <button class="btn-dispatch" onclick="openModal('${{g.id}}')">READ FULL DISPATCH</button>`;
            grid.appendChild(card);
        }});
        function openModal(id) {{
            const g = games.find(x => x.id === id);
            document.getElementById('modal-title').innerText = g.away.name + " @ " + g.home.name;
            document.getElementById('modal-body').innerText = g.story;
            document.getElementById('modal').style.display = 'flex';
        }}
        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
    </script>
    </body></html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    seen_ids = set()
    
    leagues = [
        ("basketball", "nba"), ("basketball", "mens-college-basketball"), 
        ("hockey", "nhl"), ("hockey", "mens-college-hockey"),
        ("football", "nfl"), ("baseball", "mlb")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen_ids))
    
    all_games.extend(get_cricket_wc(whitelist))
    
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
