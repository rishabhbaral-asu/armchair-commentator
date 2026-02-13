import requests
import json
from datetime import datetime, timedelta
import os
import sys
import re  # Added for strict regex matching

# --- CONFIGURATION ---
WHITELIST_FILE = "scripts/whitelist.txt"  # File containing team names (one per line)
DATE_WINDOW_DAYS = 3  # How many days ahead to look
# ---------------------

def load_whitelist():
    """Loads team names from a local file."""
    if not os.path.exists(WHITELIST_FILE):
        print(f"Error: {WHITELIST_FILE} not found. Please create it with one team name per line.")
        sys.exit(1)
    
    with open(WHITELIST_FILE, "r") as f:
        # distinct lines, stripped of whitespace, ignoring empty lines
        return list(set(line.strip().lower() for line in f if line.strip()))

def is_match(text, whitelist):
    """
    STRICT MATCHING: Uses Regex Word Boundaries (\b) to prevent
    'India' from matching 'Indiana'.
    """
    if not text:
        return False
        
    text_clean = text.lower()
    
    for item in whitelist:
        # \b ensures we match "India" as a whole word, not part of "Indiana"
        # re.escape ensures special characters in team names (like + or .) don't break regex
        pattern = r'\b' + re.escape(item) + r'\b'
        
        if re.search(pattern, text_clean):
            return True
    return False

def get_espn_data(sport, league, whitelist):
    """Fetches data from ESPN's internal APIs."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    
    # We ask for a wide limit to get everything, then filter locally
    params = {
        "limit": "900",
        "dates": get_date_param() 
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        games = []
        for event in data.get("events", []):
            short_name = event.get("shortName", "")
            name = event.get("name", "")
            
            # Check if this game involves a whitelisted team
            if is_match(short_name, whitelist) or is_match(name, whitelist):
                comp = event["competitions"][0]
                status_type = event["status"]["type"]["state"] # pre, in, post
                
                # Get score data
                competitors = comp.get("competitors", [])
                match_str = []
                
                # Format: "Team A (10) vs Team B (4)"
                for c in competitors:
                    team_name = c["team"]["displayName"]
                    score = c.get("score", "0")
                    match_str.append(f"{team_name} {score}")
                
                start_time = event.get("date", "Unknown Time")
                
                # Convert UTC string to local object for sorting
                try:
                    dt_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                    # Quick/Dirty Local Time conversion (adjust hours as needed, e.g. -5 for EST)
                    # For a real app, use pytz. Here we just strip the T/Z for readability.
                    display_time = dt_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    display_time = start_time

                games.append({
                    "sport": league.upper(),
                    "matchup": " vs ".join([c["team"]["displayName"] for c in competitors]),
                    "status": status_type,
                    "score": " - ".join([f"{c['team']['abbreviation']} {c.get('score','0')}" for c in competitors]),
                    "time": display_time,
                    "raw_dt": dt_obj if 'dt_obj' in locals() else datetime.max
                })
        return games
        
    except Exception as e:
        # print(f"Error fetching {sport}/{league}: {e}") # Uncomment for deep debug
        return []

def get_bbc_cricket(whitelist):
    """
    Fetches Cricket data from BBC.
    This is often more reliable for International/County cricket than ESPN.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=DATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    
    # BBC Morph API endpoint
    url = f"https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-commentary%2FendDate%2F{end_date}%2FstartDate%2F{today}%2FtodayDate%2F{today}%2Fversion%2F2.4.6"
    
    games = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"[DEBUG] BBC Cricket API failed with status {resp.status_code}")
            return []
            
        data = resp.json()
        payload = data.get("payload", [])
        
        # Debug helper: Count raw games found
        raw_game_count = 0
        
        for item in payload:
            body = item.get("body", {})
            match_list = body.get("matchList", [])
            
            for match in match_list:
                raw_game_count += 1
                home = match.get("homeTeam", {}).get("name", "")
                away = match.get("awayTeam", {}).get("name", "")
                slug = f"{home} vs {away}"
                
                # STRICT MATCH CHECK
                if is_match(slug, whitelist):
                    # Status
                    state = match.get("status", "fixture") # fixture, live, result
                    
                    # Scores
                    home_runs = match.get("homeTeam", {}).get("scores", "")
                    away_runs = match.get("awayTeam", {}).get("scores", "")
                    
                    score_str = f"{home} {home_runs} - {away} {away_runs}"
                    
                    # Time
                    timestamp = match.get("startTime", "") # often omitted if live
                    display_time = "LIVE/TODAY"
                    raw_dt = datetime.now()
                    
                    if timestamp:
                        try:
                            # BBC timestamps sometimes vary, usually ISO
                            dt_obj = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
                            display_time = dt_obj.strftime("%Y-%m-%d %H:%M")
                            raw_dt = dt_obj
                        except:
                            pass

                    games.append({
                        "sport": "CRICKET",
                        "matchup": slug,
                        "status": state,
                        "score": score_str,
                        "time": display_time,
                        "raw_dt": raw_dt
                    })
        
        # DEBUG: Toggle this if you suspect data is missing
        # print(f"[DEBUG] BBC Cricket found {raw_game_count} total games. Matching: {len(games)}")
        
        return games

    except Exception as e:
        print(f"[DEBUG] Error fetching Cricket: {e}")
        return []

def get_date_param():
    """Returns YYYYMMDD-YYYYMMDD string for ESPN."""
    start = datetime.now()
    end = start + timedelta(days=DATE_WINDOW_DAYS)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"

def main():
    print(f"--- Sports Dashboard (Next {DATE_WINDOW_DAYS} Days) ---")
    
    whitelist = load_whitelist()
    print(f"Tracking {len(whitelist)} teams/keywords.")
    # print(f"DEBUG: Whitelist: {whitelist}") # Uncomment to verify loaded names

    all_games = []

    # 1. ESPN Sources
    sources = [
        ("basketball", "nba"),
        ("basketball", "mens-college-basketball"),
        ("football", "nfl"),
        ("hockey", "nhl"),
        ("soccer", "eng.1"), # Premier League
        ("soccer", "esp.1"), # La Liga
        ("soccer", "usa.1"), # MLS
        ("baseball", "mlb"),
    ]

    print("Fetching ESPN data...", end="", flush=True)
    for sport, league in sources:
        print(".", end="", flush=True)
        all_games.extend(get_espn_data(sport, league, whitelist))
    print(" Done.")

    # 2. Cricket Source (BBC)
    print("Fetching Cricket data...", end="", flush=True)
    cricket_games = get_bbc_cricket(whitelist)
    all_games.extend(cricket_games)
    print(" Done.")

    # 3. Sort and Display
    if not all_games:
        print("\n\nNo games found for your teams in the next 3 days.")
        print("Tip: Check 'whitelist.txt' spelling. Ensure 'India' is on its own line.")
    else:
        # Sort by time
        all_games.sort(key=lambda x: x["raw_dt"])
        
        print(f"\n\n{'TIME':<20} | {'SPORT':<10} | {'MATCHUP':<40} | {'SCORE/STATUS'}")
        print("-" * 100)
        
        for game in all_games:
            print(f"{game['time']:<20} | {game['sport']:<10} | {game['matchup']:<40} | {game['score']} ({game['status']})")

if __name__ == "__main__":
    main()
