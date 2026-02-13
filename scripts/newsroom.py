import requests
import json
from datetime import datetime, timedelta
import os
import sys
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"
DATE_WINDOW_DAYS = 5  # Look ahead 5 days
# ---------------------

def load_whitelist():
    """Loads team names from a local file."""
    # Handle paths for local vs GitHub Actions
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    selected_path = WHITELIST_FILE
    for p in paths:
        if os.path.exists(p):
            selected_path = p
            break
            
    if not os.path.exists(selected_path):
        print(f"⚠️ Warning: {WHITELIST_FILE} not found. Using empty whitelist.")
        return []
    
    with open(selected_path, "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

def is_match(text, whitelist):
    """
    STRICT MATCHING:
    - \b ensures "India" matches "India" but NOT "Indiana".
    """
    if not text: return False
    text_clean = text.lower()
    
    for item in whitelist:
        # Escape special chars (like + or .) but allow word boundaries
        pattern = r'\b' + re.escape(item) + r'\b'
        if re.search(pattern, text_clean):
            return True
    return False

def get_espn_data(sport, league, whitelist):
    """Fetches games from ESPN's hidden API."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "900", "dates": get_date_param()}
    
    print(f"   Scanning {league}...", end="\r") 
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        games = []
        for event in data.get("events", []):
            short_name = event.get("shortName", "")
            name = event.get("name", "")
            
            # Check if this game involves a whitelist team
            if is_match(short_name, whitelist) or is_match(name, whitelist):
                comp = event["competitions"][0]
                competitors = comp.get("competitors", [])
                
                # Format: "Home vs Away"
                match_str = " vs ".join([c["team"]["displayName"] for c in competitors])
                
                # Score: "LAL 102 - BOS 99"
                score_parts = []
                for c in competitors:
                    team_score = c.get("score", "0")
                    # Try to get abbreviation, fallback to first 3 letters
                    team_abv = c["team"].get("abbreviation", c["team"].get("displayName", "UNK")[:3].upper())
                    score_parts.append(f"{team_abv} {team_score}")
                score_str = " - ".join(score_parts)
                
                status = event["status"]["type"]["state"]
                start_time = event.get("date", "Unknown")
                
                # Time Parsing
                try:
                    dt_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                    display_time = dt_obj.strftime("%Y-%m-%d %H:%M UTC")
                except:
                    display_time = start_time
                    dt_obj = datetime.max
                
                # Pretty print the league name
                sport_display = league.upper().replace(".1", "").replace("MENS-", "").replace("COLLEGE-", "NCAA ")

                games.append({
                    "sport": sport_display,
                    "matchup": match_str,
                    "score": score_str,
                    "status": status,
                    "time": display_time,
                    "raw_dt": dt_obj
                })
        return games
    except Exception as e:
        return []

def get_bbc_cricket(whitelist):
    """Fetches Cricket data from BBC."""
    print(f"   Scanning Cricket (BBC)...", end="\r")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=DATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    
    url = f"https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-commentary%2FendDate%2F{end_date}%2FstartDate%2F{today}%2FtodayDate%2F{today}%2Fversion%2F2.4.6"
    
    games = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return []
            
        payload = resp.json().get("payload", [])
        
        for item in payload:
            body = item.get("body", {})
            match_list = body.get("matchList", [])
            
            for match in match_list:
                home = match.get("homeTeam", {}).get("name", "")
                away = match.get("awayTeam", {}).get("name", "")
                slug = f"{home} vs {away}"
                
                if is_match(slug, whitelist):
                    state = match.get("status", "fixture")
                    home_runs = match.get("homeTeam", {}).get("scores", "")
                    away_runs = match.get("awayTeam", {}).get("scores", "")
                    score_str = f"{home} {home_runs} - {away} {away_runs}"
                    
                    timestamp = match.get("startTime", "")
                    display_time = "LIVE/TODAY"
                    raw_dt = datetime.now()
                    
                    if timestamp:
                        try:
                            dt_obj = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
                            display_time = dt_obj.strftime("%Y-%m-%d %H:%M UTC")
                            raw_dt = dt_obj
                        except: pass

                    games.append({
                        "sport": "CRICKET",
                        "matchup": slug,
                        "status": state,
                        "score": score_str,
                        "time": display_time,
                        "raw_dt": raw_dt
                    })
        return games

    except Exception:
        return []

def get_date_param():
    start = datetime.now()
    end = start + timedelta(days=DATE_WINDOW_DAYS)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"

def generate_html(games):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tempe Torch Sports Wire</title>
        <meta http-equiv="refresh" content="1800">
        <style>
            body { font-family: 'Verdana', sans-serif; background: #1a1a1a; color: #ddd; padding: 20px; max-width: 800px; margin: auto; }
            h1 { border-bottom: 3px solid #e91e63; padding-bottom: 10px; color: #fff; text-transform: uppercase; letter-spacing: 2px; }
            .game { background: #2d2d2d; padding: 15px; margin-bottom: 15px; border-radius: 8px; border-left: 5px solid #e91e63; }
            .header { display: flex; justify-content: space-between; font-size: 0.85em; color: #888; margin-bottom: 5px; }
            .matchup { font-size: 1.2em; font-weight: bold; color: #fff; margin-bottom: 5px; }
            .score { font-size: 1.1em; color: #4caf50; font-family: monospace; }
            .status { font-size: 0.9em; color: #ff9800; margin-top: 5px; }
            .empty { color: #666; font-style: italic; }
            .footer { margin-top: 40px; font-size: 0.8em; color: #555; text-align: center; }
        </style>
    </head>
    <body>
        <h1>Tempe Torch • Sports Wire</h1>
    """
    
    if not games:
        html += f"<p class='empty'>No active games found for tracked teams in the next {DATE_WINDOW_DAYS} days.</p>"
    else:
        for game in games:
            html += f"""
            <div class="game">
                <div class="header">
                    <span>{game['sport']}</span>
                    <span>{game['time']}</span>
                </div>
                <div class="matchup">{game['matchup']}</div>
                <div class="score">{game['score']}</div>
                <div class="status">{game['status']}</div>
            </div>
            """
            
    html += f"""
        <div class="footer">
            Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        </div>
    </body>
    </html>
    """
    return html

def main():
    print("--- STARTING NEWSROOM ---")
    whitelist = load_whitelist()
    print(f"📋 Whitelist loaded: {len(whitelist)} teams")
    
    all_games = []
    
    sources = [
        # --- US PRO ---
        ("basketball", "nba"),
        ("football", "nfl"),
        ("hockey", "nhl"),
        ("baseball", "mlb"),
        
        # --- COLLEGE SPORTS ---
        ("basketball", "mens-college-basketball"),
        ("hockey", "mens-college-hockey"), # NEW!
        ("baseball", "college-baseball"),
        ("softball", "college-softball"),
        
        # --- SOCCER (UK) ---
        ("soccer", "eng.1"), # Premier League
        ("soccer", "eng.2"), # Championship
        ("soccer", "eng.3"), # League One
        
        # --- SOCCER (EUROPE) ---
        ("soccer", "ita.1"), # Serie A
        ("soccer", "ger.1"), # Bundesliga
        ("soccer", "fra.1"), # Ligue 1
        ("soccer", "esp.1"), # La Liga
        ("soccer", "uefa.champions"), # UCL
        
        # --- SOCCER (US) ---
        ("soccer", "usa.1"), # MLS
        ("soccer", "usa.nwsl"), # NWSL
    ]
    
    for sport, league in sources:
        all_games.extend(get_espn_data(sport, league, whitelist))
    
    # Cricket (BBC)
    all_games.extend(get_bbc_cricket(whitelist))
    
    # Sort by time
    all_games.sort(key=lambda x: x["raw_dt"])
    
    # Write HTML
    html = generate_html(all_games)
    
    output_path = OUTPUT_FILE
    if os.path.exists("..") and os.path.basename(os.getcwd()) == "scripts":
        output_path = os.path.join("..", OUTPUT_FILE)

    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"\n✅ DONE. Wrote {len(all_games)} games to {output_path}")

if __name__ == "__main__":
    main()
