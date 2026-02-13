import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"
DAYS_BACK = 5
DAYS_AHEAD = 3
# ---------------------

def load_whitelist():
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return [line.strip().lower() for line in f if line.strip()]
    return []

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    for item in whitelist:
        if re.search(r'\b' + re.escape(item) + r'\b', text_clean):
            return True
    return False

def get_game_data(sport, league, whitelist):
    """Fetches scores and deep-links to stories."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    date_str = f"{(datetime.now()-timedelta(days=DAYS_BACK)).strftime('%Y%m%d')}-{(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime('%Y%m%d')}"
    params = {"limit": "150", "dates": date_str}
    
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                comp = event["competitions"][0]
                home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                
                # Fetch Story
                story_text = "Analysis is being filed by the press box. Check back shortly."
                summary_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event['id']}"
                try:
                    s_data = requests.get(summary_url, timeout=5).json()
                    articles = s_data.get("news", {}).get("articles", [])
                    if articles:
                        # Ensure the article title or description mentions one of the teams
                        content = articles[0].get("story", articles[0].get("description", ""))
                        if content: story_text = re.sub('<[^<]+?>', '', content)
                except: pass

                games.append({
                    "id": event['id'],
                    "sport": league.upper().replace(".1","").replace("MENS-","").replace("COLLEGE-","NCAA "),
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": home["team"]["displayName"], "logo": home["team"].get("logo", ""), "score": home.get("score", "0")},
                    "away": {"name": away["team"]["displayName"], "logo": away["team"].get("logo", ""), "score": away.get("score", "0")},
                    "story": story_text,
                    "date": event.get("date")
                })
        return games
    except: return []

def get_cricket(whitelist):
    """Specialized Cricket Fetcher (ESPN Global)"""
    url = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/scoreboard"
    try:
        data = requests.get(url, timeout=10).json()
        cricket_games = []
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                comp = event["competitions"][0]
                cricket_games.append({
                    "id": event['id'],
                    "sport": "CRICKET",
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": comp['competitors'][0]['team']['displayName'], "logo": "https://a.espncdn.com/i/teamlogos/cricket/500/default.png", "score": comp['competitors'][0].get("score", "N/A")},
                    "away": {"name": comp['competitors'][1]['team']['displayName'], "logo": "https://a.espncdn.com/i/teamlogos/cricket/500/default.png", "score": comp['competitors'][1].get("score", "N/A")},
                    "story": "International coverage provided by ESPN Cricket. Click for live updates.",
                    "date": event.get("date")
                })
        return cricket_games
    except: return []

def generate_html(games):
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Tempe Torch Newsroom</title>
        <style>
            :root {{ --bg: #121212; --card: #1e1e1e; --accent: #ff3d00; --text: #efefef; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
            .card {{ background: var(--card); border-radius: 12px; padding: 20px; position: relative; display: flex; flex-direction: column; }}
            .sport-label {{ font-size: 0.7rem; font-weight: bold; color: var(--accent); text-transform: uppercase; margin-bottom: 10px; }}
            .teams {{ display: flex; justify-content: space-between; align-items: center; }}
            .team {{ text-align: center; width: 40%; }}
            .logo-bg {{ background: white; border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; padding: 5px; }}
            .logo-bg img {{ max-width: 100%; max-height: 100%; }}
            .score {{ font-size: 1.8rem; font-weight: 800; }}
            .status {{ text-align: center; font-size: 0.8rem; color: #aaa; margin: 15px 0; }}
            .read-btn {{ background: #333; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
            .read-btn:hover {{ background: var(--accent); }}
            
            /* Modal */
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 100; justify-content: center; align-items: center; }}
            .modal-content {{ background: #222; width: 90%; max-width: 700px; padding: 40px; border-radius: 15px; position: relative; max-height: 80vh; overflow-y: auto; }}
            .close-btn {{ position: absolute; top: 20px; right: 20px; font-size: 2rem; cursor: pointer; color: var(--accent); }}
            .story-body {{ line-height: 1.6; font-size: 1.1rem; color: #ccc; }}
        </style>
    </head>
    <body>
        <header>
            <h1>TEMPE TORCH <span style="font-weight:100">NEWSROOM</span></h1>
            <div id="clock"></div>
        </header>

        <div class="grid" id="game-grid"></div>

        <div id="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
                <h2 id="modal-title"></h2>
                <div class="story-body" id="modal-story"></div>
            </div>
        </div>

        <script>
            const games = {games_json};
            const grid = document.getElementById('game-grid');

            function updateClock() {{
                const now = new Date();
                document.getElementById('clock').innerText = now.toLocaleString('en-US', {{ timeZone: 'America/Phoenix', hour: '2-digit', minute: '2-digit', second: '2-digit' }}) + " AZT";
            }}
            setInterval(updateClock, 1000); updateClock();

            games.sort((a,b) => new Date(b.date) - new Date(a.date));

            games.forEach(g => {{
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="sport-label">${{g.sport}}</div>
                    <div class="teams">
                        <div class="team">
                            <div class="logo-bg"><img src="${{g.away.logo}}"></div>
                            <div style="font-size:0.9rem">${{g.away.name}}</div>
                            <div class="score">${{g.away.score}}</div>
                        </div>
                        <div style="color:#444">VS</div>
                        <div class="team">
                            <div class="logo-bg"><img src="${{g.home.logo}}"></div>
                            <div style="font-size:0.9rem">${{g.home.name}}</div>
                            <div class="score">${{g.home.score}}</div>
                        </div>
                    </div>
                    <div class="status">${{g.detail}}</div>
                    <button class="read-btn" onclick="openModal('${{g.id}}')">Read Analysis</button>
                `;
                grid.appendChild(card);
            }});

            function openModal(id) {{
                const game = games.find(x => x.id === id);
                document.getElementById('modal-title').innerText = game.away.name + " at " + game.home.name;
                document.getElementById('modal-story').innerText = game.story;
                document.getElementById('modal').style.display = 'flex';
            }}

            function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
        </script>
    </body>
    </html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl"), ("baseball", "mlb"),
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), 
        ("baseball", "college-baseball"), ("softball", "college-softball"),
        ("soccer", "eng.1"), ("soccer", "eng.2"), ("soccer", "eng.3"),
        ("soccer", "ita.1"), ("soccer", "ger.1")
    ]
    for sport, league in sources:
        all_games.extend(get_game_data(sport, league, whitelist))
    
    all_games.extend(get_cricket(whitelist))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
