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

# --- 2. THE CORRECTED STORY ENGINE ---

def craft_ap_story(event, sport, league):
    """Fetches news specifically TIED to this game ID only."""
    status_type = event["status"]["type"]["name"]
    eid = event["id"]
    comp = event["competitions"][0]
    home = comp["competitors"][0]["team"]["shortDisplayName"]
    away = comp["competitors"][1]["team"]["shortDisplayName"]
    
    # FETCH SUMMARY FOR THIS SPECIFIC GAME
    try:
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
        detail = requests.get(url, timeout=5).json()
        
        # VALIDATION: Ensure the news article actually mentions these teams
        articles = detail.get("news", {}).get("articles", [])
        if articles:
            headline = articles[0].get('headline', '')
            description = articles[0].get('description', '')
            # Only return if the headline matches the context of the teams involved
            if home.lower() in headline.lower() or away.lower() in headline.lower():
                return f"<b>{headline.upper()}</b><br><br>— {description}"
    except:
        pass

    # FALLBACK: If no specific AP story exists yet, build a custom narrative for THESE teams
    city = comp.get("venue", {}).get("address", {}).get("city", "Site").upper()
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    if status_type == "STATUS_FINAL":
        h_score = int(comp["competitors"][0]["score"])
        a_score = int(comp["competitors"][1]["score"])
        win = home if h_score > a_score else away
        los = away if h_score > a_score else home
        return f"<b>{win.upper()} SECURES VICTORY AT {venue}</b><br><br>The {win} outlasted {los} in a hard-fought battle in {city}, finishing with a final score of {max(h_score, a_score)}-{min(h_score, a_score)}."

    # PREVIEW LOGIC
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    diff = time_ms - datetime.now(MST)
    countdown = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    return f"<b>PREVIEW: {away.upper()} @ {home.upper()}</b><br><br><b>T-MINUS {countdown}</b>. Tip-off scheduled for {time_ms.strftime('%A at %I:%M %p')} MST."

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
            # Match whitelist against full team names
            match = False
            for t in comp["competitors"]:
                full_name = t['team'].get('displayName','').lower()
                if any(w in full_name for w in whitelist): match = True
            
            if match and eid not in seen_ids:
                results.append({
                    "id": eid, "iso_date": event["date"], "sport_type": sport,
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "story": craft_ap_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. EXACT AESTHETICS REPLICATION ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@400;700&display=swap');
    body { background: #0f1113; color: #eee; font-family: 'Roboto Condensed', sans-serif; padding: 40px; }
    .container { max-width: 900px; margin: auto; }

    /* NBC NHL TOP-BAR STYLE */
    .bug-hockey { display: flex; background: linear-gradient(180deg, #2c2f36 0%, #000 100%); border: 1px solid #444; height: 50px; align-items: stretch; margin-top: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.9em; text-transform: uppercase; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 700; gap: 10px; border-right: 1px solid #333; }
    .hockey-team img { height: 32px; width: 32px; }
    .hockey-score { width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; font-family: 'Oswald'; background: rgba(0,0,0,0.4); }

    /* ESPN NCAA FLAT STYLE */
    .bug-ncaa { display: flex; background: #fff; color: #000; height: 70px; align-items: stretch; margin-top: 40px; border-left: 10px solid #000; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.5em; font-weight: 800; text-transform: uppercase; gap: 12px; }
    .ncaa-team img { height: 45px; width: 45px; }
    .ncaa-score { background: #000; color: #fff; width: 90px; display: flex; align-items: center; justify-content: center; font-size: 2.5em; font-family: 'Oswald'; }
    .ncaa-status { background: #e2e2e2; width: 120px; display: flex; align-items: center; justify-content: center; font-size: 0.85em; font-weight: bold; border-left: 1px solid #ccc; text-align: center; color: #444; }

    .wire-box { background: #fff; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.6; font-size: 1.15em; margin-bottom: 60px; border-top: 1px solid #ddd; }
    </style></head><body><div class="container">"""

    for g in games:
        if g['sport_type'] == "hockey":
            html += f"""<div class="bug-hockey">
                <div class="hockey-status">{g['status_text']}</div>
                <div class="hockey-team"><img src="{g['away_logo']}">{g['away_name'].upper()}</div><div class="hockey-score">{g['away_score']}</div>
                <div class="hockey-team"><img src="{g['home_logo']}">{g['home_name'].upper()}</div><div class="hockey-score">{g['home_score']}</div>
            </div>"""
        else:
            html += f"""<div class="bug-ncaa">
                <div class="ncaa-team"><img src="{g['away_logo']}">{g['away_name']}</div><div class="ncaa-score">{g['away_score']}</div>
                <div class="ncaa-team"><img src="{g['home_logo']}">{g['home_name']}</div><div class="ncaa-score">{g['home_score']}</div>
                <div class="ncaa-status">{g['status_text']}</div>
            </div>"""
        html += f'<div class="wire-box">{g["story"]}</div>'

    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    # ACTIVATED COLLEGE HOCKEY
    leagues = [("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), ("soccer", "eng.1")]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
