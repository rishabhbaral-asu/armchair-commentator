import requests
import json
from datetime import datetime, timedelta
import os
import sys
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"  # Ensure this file exists in your repo!
OUTPUT_FILE = "index.html"        # The file GitHub Pages serves
DATE_WINDOW_DAYS = 3
# ---------------------

def load_whitelist():
    """Loads team names from a local file."""
    # If running in GitHub Actions, sometimes paths need to be explicit.
    # Try local first, then look one directory up if script is in 'scripts/'
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    
    selected_path = WHITELIST_FILE
    for p in paths:
        if os.path.exists(p):
            selected_path = p
            break
            
    if not os.path.exists(selected_path):
        print(f"Warning: {WHITELIST_FILE} not found. Returning empty list.")
        return []
    
    with open(selected_path, "r") as f:
        return list(set(line.strip().lower() for line in f if line.strip()))

def is_match(text, whitelist):
    """STRICT MATCHING: Uses Regex Word Boundaries (\b)."""
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
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        games = []
        for event in data.get("events", []):
            short_name = event.get("shortName", "")
            name = event.get("name", "")
            if is_match(short_name, whitelist) or is_match(name, whitelist):
                comp = event["competitions"][0]
                competitors = comp.get("competitors", [])
                match_str = " vs ".join([c["team"]["displayName"] for c in competitors])
                score_str = " - ".join([f"{c['team']['abbreviation']} {c.get('score','0')}" for c in competitors])
                status = event["status"]["type"]["state"]
                start_time = event.get("date", "Unknown")
                
                try:
                    dt_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                    display_time = dt_obj.strftime("%Y-%m-%d %H:%M UTC")
                except:
                    display_time = start_time
                    dt_obj = datetime.max

                games.append({
                    "sport": league.upper(),
                    "matchup": match_str,
                    "score": score_str,
                    "status": status,
                    "time": display_time,
                    "raw_dt": dt_obj
                })
        return games
    except Exception:
        return []

def get_bbc_cricket(whitelist):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=DATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    url = f"https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-commentary%2FendDate%2F{end_date}%2FstartDate%2F{today}%2FtodayDate%2F{today}%2Fversion%2F2.4.6"
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
                        "score": score_str,
                        "status": match.get("status", "fixture"),
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
    """Generates a simple, clean HTML page."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tempe Torch Sports Ticker</title>
        <style>
            body { font-family: 'Courier New', Courier, monospace; background: #222; color: #0f0; padding: 20px; }
            h1 { border-bottom: 2px solid #0f0; padding-bottom: 10px; }
            .game { border: 1px solid #444; padding: 10px; margin-bottom: 10px; background: #333; }
            .time { color: #aaa; font-size: 0.9em; }
            .sport { font-weight: bold; color: #fff; }
            .matchup { font-size: 1.2em; color: #ffeb3b; }
            .score { font-size: 1.1em; font-weight: bold; }
            .footer { margin-top: 30px; color: #666; font-size: 0.8em; }
        </style>
    </head>
    <body>
        <h1>TEMPE TORCH SPORTS WIRE</h1>
    """
    
    if not games:
        html += "<p>No games scheduled for tracked teams in the next 3 days.</p>"
    else:
        for game in games:
            html += f"""
            <div class="game">
                <div class="time">{game['time']} | <span class="sport">{game['sport']}</span></div>
                <div class="matchup">{game['matchup']}</div>
                <div class="score">{game['score']}</div>
                <div class="status">Status: {game['status']}</div>
            </div>
            """
            
    html += f"""
        <div class="footer">Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
    </body>
    </html>
    """
    return html

def main():
    whitelist = load_whitelist()
    all_games = []
    
    # ESPN
    sources = [("basketball", "nba"), ("basketball", "mens-college-basketball"), 
               ("football", "nfl"), ("hockey", "nhl"), ("soccer", "eng.1"), 
               ("soccer", "esp.1"), ("soccer", "usa.1"), ("baseball", "mlb")]
    for sport, league in sources:
        all_games.extend(get_espn_data(sport, league, whitelist))
        
    # Cricket
    all_games.extend(get_bbc_cricket(whitelist))
    
    # Sort
    all_games.sort(key=lambda x: x["raw_dt"])
    
    # Write HTML
    html_content = generate_html(all_games)
    
    # Determine output path (Root directory if running from scripts/)
    output_path = OUTPUT_FILE
    if os.path.exists("..") and os.path.basename(os.getcwd()) == "scripts":
        output_path = os.path.join("..", OUTPUT_FILE)

    with open(output_path, "w") as f:
        f.write(html_content)
    
    print(f"Successfully wrote {len(all_games)} games to {output_path}")

if __name__ == "__main__":
    main()
