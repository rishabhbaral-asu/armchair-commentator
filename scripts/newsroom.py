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
                story_text = "The newsroom is awaiting the official AP recap for this match. Scoring summaries and key highlights will be updated as they arrive."
                summary_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event['id']}"
                try:
                    s_data = requests.get(summary_url, timeout=5).json()
                    articles = s_data.get("news", {}).get("articles", [])
                    if articles:
                        content = articles[0].get("story", articles[0].get("description", ""))
                        # VALIDATION: Ensure the story actually mentions one of the teams
                        if is_match(content, [home["team"]["displayName"], away["team"]["displayName"]]):
                            story_text = re.sub('<[^<]+?>', '', content)
                        else:
                            # If the story is generic filler, build a "Live Wire" status instead
                            story_text = f"STORY UPDATE: {away['team']['displayName']} and {home['team']['displayName']} are currently featured in our live wire. "
                            if event["status"]["type"]["state"] == "post":
                                story_text += f"The game concluded with a final score of {away['score']} - {home['score']}."
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
    """Cricket API fetch with specific series tracking."""
    url = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/scoreboard"
    try:
        data = requests.get(url, timeout=10).json()
        cricket_games = []
        for event in data.get("events", []):
            # Check Team names OR the league name (shortName)
            if is_match(event.get("name", ""), whitelist) or is_match(event.get("shortName", ""), whitelist):
                comp = event["competitions"][0]
                cricket_games.append({
                    "id": event['id'],
                    "sport": "CRICKET",
                    "status": event["status"]["type"]["state"],
                    "detail": event["status"]["type"]["detail"],
                    "home": {"name": comp['competitors'][0]['team']['displayName'], "logo": "https://a.espncdn.com/i/teamlogos/cricket/500/default.png", "score": comp['competitors'][0].get("score", "N/A")},
                    "away": {"name": comp['competitors'][1]['team']['displayName'], "logo": "https://a.espncdn.com/i/teamlogos/cricket/500/default.png", "score": comp['competitors'][1].get("score", "N/A")},
                    "story": f"Live coverage from {event.get('name')}. Full statistical analysis provided by the ESPN Cricket global desk.",
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
            :root {{ --bg: #0d0d0d; --card: #1a1a1a; --accent: #c62828; --text: #e0e0e0; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--accent); padding-bottom: 10px; margin-bottom: 30px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 25px; }}
            .card {{ background: var(--card); border: 1px solid #333; border-radius: 8px; padding: 20px; }}
            .sport-tag {{ background: var(--accent); color: white; padding: 2px 8px; font-size: 0.7rem; font-weight: bold; border-radius: 3px; display: inline-block; margin-bottom: 15px; }}
            .teams {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
            .team-col {{ width: 40%; text-align: center; }}
            .logo-bg {{ background: #fff; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; }}
            .logo-bg img {{ width: 80%; height: 80%; object-fit: contain; }}
            .score {{ font-size: 2rem; font-weight: bold; }}
            .status {{ font-size: 0.8rem; color: #888; text-align: center; border-top: 1px solid #333; padding-top: 10px; }}
            .read-btn {{ width: 100%; padding: 12px; background: transparent; border: 1px solid #555; color: white; cursor: pointer; border-radius: 5px; margin-top: 15px; transition: 0.3s; }}
            .read-btn:hover {{ background: #c62828; border-color: #c62828; }}
            
            #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 100; align-items: center; justify-content: center; }}
            .modal-content {{ background: #222; max-width: 800px; width: 90%; padding: 40px; border-radius: 12px; position: relative; max-height: 85vh; overflow-y: auto; }}
            .close-btn {{ position: absolute; top: 20px; right: 20px; font-size: 2rem; cursor: pointer; color: #888; }}
            .story-text {{ line-height: 1.8; font-size: 1.2rem; color: #bbb; }}
            .story-text::first-line {{ font-weight: bold; color: white; }}
        </style>
    </head>
    <body>
        <header>
            <h1>TEMPE TORCH <span style="font-weight:100">WIRE</span></h1>
            <div id="clock"></div>
        </header>

        <div class="grid" id="game-grid"></div>

        <div id="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
                <h2 id="modal-title" style="border-bottom: 2px solid #c62828; padding-bottom: 10px;"></h2>
                <div class="story-text" id="modal-story"></div>
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
                    <div class="sport-tag">${{g.sport}}</div>
                    <div class="teams">
                        <div class="team-col">
                            <div class="logo-bg"><img src="${{g.away.logo}}"></div>
                            <div style="font-size:0.8rem; font-weight:bold;">${{g.away.name}}</div>
                            <div class="score">${{g.away.score}}</div>
                        </div>
                        <div style="font-weight:bold; color:#444;">AT</div>
                        <div class="team-col">
                            <div class="logo-bg"><img src="${{g.home.logo}}"></div>
                            <div style="font-size:0.8rem; font-weight:bold;">${{g.home.name}}</div>
                            <div class="score">${{g.home.score}}</div>
                        </div>
                    </div>
                    <div class="status">${{g.detail}}</div>
                    <button class="read-btn" onclick="openModal('${{g.id}}')">READ DISPATCH</button>
                `;
                grid.appendChild(card);
            }});

            function openModal(id) {{
                const game = games.find(x => x.id === id);
                document.getElementById('modal-title').innerText = game.away.name + " @ " + game.home.name;
                document.getElementById('modal-story').innerHTML = game.story.replace(/\\n/g, '<br><br>');
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
    # Standard Leagues
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl"), ("baseball", "mlb"),
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), 
        ("baseball", "college-baseball"), ("softball", "college-softball"),
        ("soccer", "eng.1"), ("soccer", "eng.2"), ("soccer", "ita.1")
    ]
    for sport, league in sources:
        all_games.extend(get_game_data(sport, league, whitelist))
    
    all_games.extend(get_cricket(whitelist))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
