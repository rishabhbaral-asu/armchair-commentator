import requests
import json
from datetime import datetime, timedelta
import os
import sys
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"
# Window: Look back 1 day (results) and ahead 5 days
DAYS_BACK = 1
DAYS_AHEAD = 5
# ---------------------

def load_whitelist():
    """Loads team names from a local file."""
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    selected_path = WHITELIST_FILE
    for p in paths:
        if os.path.exists(p):
            selected_path = p
            break
            
    if not os.path.exists(selected_path):
        return []
    
    with open(selected_path, "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    for item in whitelist:
        pattern = r'\b' + re.escape(item) + r'\b'
        if re.search(pattern, text_clean):
            return True
    return False

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "900", "dates": get_date_param()}
    
    print(f"   Scanning {league}...", end="\r") 
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        games = []
        for event in data.get("events", []):
            short_name = event.get("shortName", "")
            name = event.get("name", "")
            
            if is_match(short_name, whitelist) or is_match(name, whitelist):
                comp = event["competitions"][0]
                competitors = comp.get("competitors", [])
                
                # --- NEW: Extract Logos & Data ---
                home_team = next((c for c in competitors if c['homeAway'] == 'home'), competitors[0])
                away_team = next((c for c in competitors if c['homeAway'] == 'away'), competitors[1])
                
                game_data = {
                    "sport": league.upper().replace(".1","").replace("MENS-","").replace("COLLEGE-","NCAA "),
                    "status": event["status"]["type"]["state"], # pre, in, post
                    "status_detail": event["status"]["type"]["detail"], # "Final", "10:00 1st"
                    "home_name": home_team["team"]["displayName"],
                    "home_logo": home_team["team"].get("logo", "https://a.espncdn.com/i/teamlogos/default-team-logo-500.png"),
                    "home_score": home_team.get("score", "0"),
                    "away_name": away_team["team"]["displayName"],
                    "away_logo": away_team["team"].get("logo", "https://a.espncdn.com/i/teamlogos/default-team-logo-500.png"),
                    "away_score": away_team.get("score", "0"),
                    "raw_utc": event.get("date", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
                }
                games.append(game_data)
        return games
    except Exception:
        return []

def get_bbc_cricket(whitelist):
    print(f"   Scanning Cricket (BBC)...", end="\r")
    # BBC Logic adjusted for back/forward window
    start_date = (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    
    url = f"https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-commentary%2FendDate%2F{end_date}%2FstartDate%2F{start_date}%2FtodayDate%2F{start_date}%2Fversion%2F2.4.6"
    
    games = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return []
        payload = resp.json().get("payload", [])
        
        for item in payload:
            for match in item.get("body", {}).get("matchList", []):
                home = match.get("homeTeam", {}).get("name", "")
                away = match.get("awayTeam", {}).get("name", "")
                slug = f"{home} vs {away}"
                
                if is_match(slug, whitelist):
                    # Cricket doesn't give nice logos in this API, use generic
                    generic_logo = "https://a.espncdn.com/i/teamlogos/cricket/500/default.png"
                    
                    timestamp = match.get("startTime", "")
                    raw_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    if timestamp: raw_utc = timestamp[:19] + "Z"

                    games.append({
                        "sport": "CRICKET",
                        "status": match.get("status", "fixture"),
                        "status_detail": match.get("matchSummaryText", match.get("status")),
                        "home_name": home,
                        "home_logo": generic_logo,
                        "home_score": match.get("homeTeam", {}).get("scores", ""),
                        "away_name": away,
                        "away_logo": generic_logo,
                        "away_score": match.get("awayTeam", {}).get("scores", ""),
                        "raw_utc": raw_utc
                    })
        return games
    except:
        return []

def get_date_param():
    # ESPN Format: YYYYMMDD-YYYYMMDD
    start = datetime.now() - timedelta(days=DAYS_BACK)
    end = datetime.now() + timedelta(days=DAYS_AHEAD)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"

def generate_html(games):
    # Convert Python Games List to a JSON object for the Javascript to handle time
    games_json = json.dumps(games)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tempe Torch Dashboard</title>
        <meta http-equiv="refresh" content="600">
        <style>
            :root {{ --bg: #121212; --card: #1e1e1e; --accent: #ffb300; --text: #e0e0e0; }}
            body {{ font-family: 'Roboto', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
            
            /* Header */
            .top-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 20px; }}
            h1 {{ margin: 0; text-transform: uppercase; letter-spacing: 1px; font-size: 1.5rem; }}
            #live-clock {{ font-family: monospace; font-size: 1.2rem; color: var(--accent); }}

            /* Grid */
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
            
            /* Game Card */
            .game-card {{ background: var(--card); border-radius: 12px; padding: 15px; position: relative; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .sport-tag {{ position: absolute; top: 10px; right: 10px; font-size: 0.7rem; background: #333; padding: 2px 6px; border-radius: 4px; color: #888; }}
            
            /* Teams Row */
            .teams {{ display: flex; justify-content: space-between; align-items: center; margin-top: 20px; }}
            .team {{ display: flex; flex-direction: column; align-items: center; width: 40%; text-align: center; }}
            .team-name {{ font-size: 0.9rem; margin-top: 8px; font-weight: bold; line-height: 1.2; }}
            
            /* Logo Pop */
            .logo-container {{ width: 60px; height: 60px; background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; padding: 5px; }}
            .logo {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
            
            /* Scores & Status */
            .versus {{ font-size: 0.8rem; color: #555; margin-top: -15px; }}
            .score-board {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 1.5rem; font-weight: bold; font-family: monospace; }}
            .score-val {{ width: 40%; text-align: center; }}
            
            /* Footer / Time */
            .game-footer {{ margin-top: 15px; border-top: 1px solid #333; padding-top: 10px; font-size: 0.85rem; text-align: center; color: #aaa; }}
            .live-indicator {{ color: #ff4444; font-weight: bold; animation: pulse 1.5s infinite; }}
            .countdown {{ color: var(--accent); }}
            
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <h1>Tempe Torch Wire</h1>
            <div id="live-clock">--:--:-- AZT</div>
        </div>
        
        <div id="game-container" class="grid"></div>

        <script>
            // --- DATA INJECTION ---
            const games = {games_json};
            
            // --- TIME ZONES ---
            // AZ is UTC-7 (No DST). We create a formatter for it.
            const azFormatter = new Intl.DateTimeFormat('en-US', {{
                timeZone: 'America/Phoenix',
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            }});

            const azDateFormatter = new Intl.DateTimeFormat('en-US', {{
                timeZone: 'America/Phoenix',
                weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
            }});

            function updateClock() {{
                const now = new Date();
                document.getElementById('live-clock').innerText = azFormatter.format(now) + " AZT";
            }}
            setInterval(updateClock, 1000);
            updateClock();

            // --- RENDER GAMES ---
            const container = document.getElementById('game-container');
            
            games.forEach(game => {{
                const card = document.createElement('div');
                card.className = 'game-card';
                
                // Parse Time
                const gameDate = new Date(game.raw_utc); // This is UTC
                const now = new Date();
                
                // Determine Status Display
                let statusHtml = "";
                let scoreHtml = `<div class="score-val">${{game.home_score}}</div><div class="score-val">${{game.away_score}}</div>`;
                
                if (game.status === 'in') {{
                    statusHtml = `<span class="live-indicator">● LIVE: ${{game.status_detail}}</span>`;
                }} else if (game.status === 'post') {{
                    statusHtml = `<span>FINAL</span>`;
                }} else {{
                    // Pre-game: Show countdown
                    const diffMs = gameDate - now;
                    const diffHrs = Math.floor(diffMs / 3600000);
                    const diffMins = Math.floor((diffMs % 3600000) / 60000);
                    
                    scoreHtml = `<div class="score-val">-</div><div class="score-val">-</div>`;
                    
                    if (diffMs > 0 && diffMs < 86400000) {{ // Within 24 hrs
                        statusHtml = `<span class="countdown">Starts in ${{diffHrs}}h ${{diffMins}}m</span>`;
                    }} else if (diffMs < 0) {{
                        statusHtml = `<span>Pending Result...</span>`;
                    }} else {{
                        statusHtml = `<span>${{azDateFormatter.format(gameDate)}}</span>`;
                    }}
                }}

                card.innerHTML = `
                    <div class="sport-tag">${{game.sport}}</div>
                    <div class="teams">
                        <div class="team">
                            <div class="logo-container">
                                <img src="${{game.home_logo}}" class="logo" onerror="this.src='https://a.espncdn.com/i/teamlogos/default-team-logo-500.png'">
                            </div>
                            <div class="team-name">${{game.home_name}}</div>
                        </div>
                        <div class="versus">vs</div>
                        <div class="team">
                            <div class="logo-container">
                                <img src="${{game.away_logo}}" class="logo" onerror="this.src='https://a.espncdn.com/i/teamlogos/default-team-logo-500.png'">
                            </div>
                            <div class="team-name">${{game.away_name}}</div>
                        </div>
                    </div>
                    <div class="score-board">${{scoreHtml}}</div>
                    <div class="game-footer">${{statusHtml}}</div>
                `;
                container.appendChild(card);
            }});
            
            if (games.length === 0) {{
                container.innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: #666;'>No games found (Yesterday - Next 5 Days).</p>";
            }}
        </script>
    </body>
    </html>
    """
    return html

def main():
    print("--- STARTING NEWSROOM 2.0 ---")
    whitelist = load_whitelist()
    print(f"📋 Whitelist loaded: {len(whitelist)} teams")
    
    all_games = []
    
    # SOURCES
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl"), ("baseball", "mlb"),
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), 
        ("baseball", "college-baseball"), ("softball", "college-softball"),
        ("soccer", "eng.1"), ("soccer", "eng.2"), ("soccer", "eng.3"),
        ("soccer", "ita.1"), ("soccer", "ger.1"), ("soccer", "fra.1"), 
        ("soccer", "esp.1"), ("soccer", "uefa.champions"),
        ("soccer", "usa.1"), ("soccer", "usa.nwsl"),
    ]
    
    for sport, league in sources:
        all_games.extend(get_espn_data(sport, league, whitelist))
    
    all_games.extend(get_bbc_cricket(whitelist))
    all_games.sort(key=lambda x: x["raw_utc"])
    
    # WRITE
    html = generate_html(all_games)
    output_path = OUTPUT_FILE
    if os.path.exists("..") and os.path.basename(os.getcwd()) == "scripts":
        output_path = os.path.join("..", OUTPUT_FILE)

    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"\n✅ DONE. Wrote {len(all_games)} games to {output_path}")

if __name__ == "__main__":
    main()
