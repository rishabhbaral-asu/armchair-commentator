import requests
import json
from datetime import datetime, timedelta
import pytz
import re
import os

# --- 1. CONFIG ---
MST = pytz.timezone('US/Arizona')
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"

def get_whitelist():
    with open("scripts/whitelist.txt", "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

def clean_html(raw_text):
    if not raw_text: return ""
    # Strip HTML tags (like <a> and <h2>) and clean up \u003C etc.
    clean = re.sub('<[^<]+?>', '', raw_text)
    # Convert newlines and carriage returns to HTML breaks for the box
    clean = clean.replace('\n', '<br>').replace('\r', '')
    return clean

# --- 2. WEATHER & STORY ENGINES ---

def get_live_weather(city):
    """Accurate local weather via OpenWeather."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        temp = round(res['main']['temp'])
        cond = res['weather'][0]['main'].upper()
        return f"{temp}°F | {cond}"
    except:
        return "72°F | CLEAR"

def fetch_wire_story(eid, sport, league, is_final):
    """Directly grabs the 'story' or 'analysis' string from the JSON root."""
    url_type = "summary" if is_final else "preview"
    attr = "story" if is_final else "analysis"
    url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/{url_type}?event={eid}"
    
    try:
        data = requests.get(url, timeout=5).json()
        # Grabbing the attribute directly as a string
        raw_text = data.get(attr, "")
        
        # If the API returns a dictionary instead of a string (failsafe), extract description
        if isinstance(raw_text, dict):
            raw_text = raw_text.get('description', '')
            
        return clean_html(raw_text)
    except:
        return "Wire report currently unavailable."

# --- 3. DATA FETCHING ---

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    today = datetime.now(MST).strftime('%Y%m%d')
    params = {"limit": "100", "dates": f"{today}-{(datetime.now(MST)+timedelta(days=2)).strftime('%Y%m%d')}"}
    if "college" in league: params["groups"] = "50"

    results = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            comp = event["competitions"][0]
            
            match = False
            for t in comp["competitors"]:
                full_name = t['team'].get('displayName','').lower()
                if any(w in full_name for w in whitelist): match = True
            
            if match and eid not in seen_ids:
                is_final = event["status"]["type"]["name"] == "STATUS_FINAL"
                city = comp.get("venue", {}).get("address", {}).get("city", "Tempe")
                
                results.append({
                    "id": eid, "iso_date": event["date"], "sport_type": sport,
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "weather": get_live_weather(city),
                    "story": fetch_wire_story(eid, sport, league, is_final)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. THE RENDERER (EXACT AESTHETICS) ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@400;700&display=swap');
    body { background: #0b0d0e; color: #eee; font-family: 'Roboto Condensed', sans-serif; padding: 40px; margin: 0; }
    .container { max-width: 900px; margin: auto; }

    /* NBC NHL STYLE - Dark Gradient, Red Status */
    .bug-hockey { display: flex; background: linear-gradient(180deg, #2c2f36 0%, #000 100%); border: 1px solid #444; height: 50px; align-items: stretch; margin-top: 40px; }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.9em; text-transform: uppercase; }
    .hockey-weather { background: #1a1a1a; color: #00eeff; padding: 0 12px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.8em; border-right: 1px solid #333; border-left: 1px solid #333; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 700; gap: 10px; border-right: 1px solid #333; text-transform: uppercase; letter-spacing: 0.5px; }
    .hockey-team img { height: 32px; width: 32px; object-fit: contain; }
    .hockey-score { width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; font-family: 'Oswald'; background: rgba(0,0,0,0.4); }

    /* ESPN NCAA STYLE - White bar, Black Scores */
    .bug-ncaa { background: #fff; color: #000; margin-top: 40px; border-left: 10px solid #000; display: flex; flex-direction: column; }
    .ncaa-main { display: flex; height: 75px; align-items: stretch; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.5em; font-weight: 800; text-transform: uppercase; gap: 12px; }
    .ncaa-team img { height: 45px; width: 45px; object-fit: contain; }
    .ncaa-score { background: #000; color: #fff; width: 90px; display: flex; align-items: center; justify-content: center; font-size: 2.5em; font-family: 'Oswald'; }
    .ncaa-status { background: #e2e2e2; width: 130px; display: flex; align-items: center; justify-content: center; font-size: 0.85em; font-weight: bold; border-left: 1px solid #ccc; text-align: center; color: #444; text-transform: uppercase; }
    .ncaa-weather-bar { background: #f4f4f4; color: #cc0000; font-size: 0.8em; padding: 6px 20px; font-weight: bold; border-top: 1px solid #ddd; text-transform: uppercase; font-family: 'Oswald'; letter-spacing: 1px; }

    .wire-box { background: #fff; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.6; font-size: 1.15em; margin-bottom: 60px; border-top: 1px solid #ddd; box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
    </style></head><body><div class="container">"""

    for g in games:
        if g['sport_type'] == "hockey":
            html += f"""<div class="bug-hockey">
                <div class="hockey-status">{g['status_text']}</div>
                <div class="hockey-weather">{g['weather']}</div>
                <div class="hockey-team"><img src="{g['away_logo']}">{g['away_name']}</div><div class="hockey-score">{g['away_score']}</div>
                <div class="hockey-team"><img src="{g['home_logo']}">{g['home_name']}</div><div class="hockey-score">{g['home_score']}</div>
            </div>"""
        else:
            html += f"""<div class="bug-ncaa">
                <div class="ncaa-main">
                    <div class="ncaa-team"><img src="{g['away_logo']}">{g['away_name']}</div><div class="ncaa-score">{g['away_score']}</div>
                    <div class="ncaa-team"><img src="{g['home_logo']}">{g['home_name']}</div><div class="ncaa-score">{g['home_score']}</div>
                    <div class="ncaa-status">{g['status_text']}</div>
                </div>
                <div class="ncaa-weather-bar">LIVE CONDITIONS: {g['weather']}</div>
            </div>"""
        html += f'<div class="wire-box">{g["story"]}</div>'

    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey")]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
