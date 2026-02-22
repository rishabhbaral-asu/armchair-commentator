import requests
import json
from datetime import datetime, timedelta
import pytz
import re
import os

# --- 1. CONFIG & WHITELIST ---
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    with open("scripts/whitelist.txt", "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

# --- 2. DUAL-ROUTING STORY ENGINE ---

def craft_ap_story(event, sport, league):
    """
    Recaps: Hits /summary and fetches 'story'
    Previews: Hits /preview and fetches 'analysis'
    """
    eid = event["id"]
    status_type = event["status"]["type"]["name"]
    
    # 1. Determine Endpoint and Target Key
    if status_type == "STATUS_FINAL":
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
        target_key = "story"
    else:
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/preview?event={eid}"
        target_key = "analysis"

    try:
        response = requests.get(url, timeout=5).json()
        
        # 2. Fetch the specific attribute from the JSON
        # The 'story' attribute in summary and 'analysis' in preview usually live here:
        content_data = response.get(target_key, {})
        
        # If it's a recap 'story', it often contains 'header' and 'description'
        if target_key == "story":
            headline = content_data.get("header", "GAME RECAP").upper()
            body = content_data.get("description", "")
            if body: return f"<b>{headline}</b><br><br>— {body}"
        
        # If it's a preview 'analysis', it often contains 'preview' or 'shortDescription'
        if target_key == "analysis":
            headline = f"ANALYSIS: {event['competitions'][0]['competitors'][1]['team']['shortDisplayName']} @ {event['competitions'][0]['competitors'][0]['team']['shortDisplayName']}".upper()
            body = content_data.get("preview", content_data.get("shortDescription", ""))
            if body: return f"<b>{headline}</b><br><br>— {body}"
            
    except Exception as e:
        print(f"Error fetching {target_key} for {eid}: {e}")

    # 3. Dynamic Fallback (if the story/analysis tags are empty in the API)
    comp = event["competitions"][0]
    home = comp["competitors"][0]["team"]["shortDisplayName"]
    away = comp["competitors"][1]["team"]["shortDisplayName"]
    
    if status_type == "STATUS_FINAL":
        return f"<b>{home.upper()} vs {away.upper()}</b><br><br>The game has concluded. Official AP wire report is pending for this matchup."
    else:
        time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
        return f"<b>UPCOMING: {away.upper()} @ {home.upper()}</b><br><br>Broadcast analysis will be available closer to the {time_ms.strftime('%I:%M %p')} MST start time."

# --- 3. DATA FETCHING (INCLUDES COLLEGE HOCKEY) ---

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
            
            # Match whitelist
            match = False
            for t in comp["competitors"]:
                name_blob = f"{t['team'].get('displayName','')} {t['team'].get('shortDisplayName','')} {t['team'].get('name','')}".lower()
                if any(re.search(rf'\b{re.escape(w)}\b', name_blob) for w in whitelist):
                    match = True
            
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

# --- 4. EXACT UI REPLICATION ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@400;700&display=swap');
    body { background: #0f1113; color: #eee; font-family: 'Roboto Condensed', sans-serif; padding: 40px; margin: 0; }
    .container { max-width: 900px; margin: auto; }

    /* NBC NHL TOP-BAR STYLE */
    .bug-hockey { display: flex; background: linear-gradient(180deg, #2c2f36 0%, #000 100%); border: 1px solid #444; height: 50px; align-items: stretch; margin-top: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.9em; text-transform: uppercase; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 700; gap: 10px; border-right: 1px solid #333; }
    .hockey-team img { height: 32px; width: 32px; }
    .hockey-score { width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; font-family: 'Oswald'; background: rgba(0,0,0,0.4); }

    /* ESPN NCAA FLAT STYLE */
    .bug-ncaa { display: flex; background: #fff; color: #000; height: 75px; align-items: stretch; margin-top: 40px; border-left: 10px solid #000; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.5em; font-weight: 800; text-transform: uppercase; gap: 12px; }
    .ncaa-team img { height: 45px; width: 45px; }
    .ncaa-score { background: #000; color: #fff; width: 90px; display: flex; align-items: center; justify-content: center; font-size: 2.5em; font-family: 'Oswald'; }
    .ncaa-status { background: #e2e2e2; width: 130px; display: flex; align-items: center; justify-content: center; font-size: 0.85em; font-weight: bold; border-left: 1px solid #ccc; text-align: center; color: #444; }

    .wire-box { background: #fff; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.6; font-size: 1.15em; margin-bottom: 60px; border-top: 1px solid #ddd; }
    </style></head><body><div class="container">
    <h1 style="font-family:'Oswald'; border-left: 6px solid #ffc627; padding-left: 20px; letter-spacing: 2px;">THE WIRE</h1>"""

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
    leagues = [("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), ("soccer", "eng.1")]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
