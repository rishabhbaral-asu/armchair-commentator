import requests
import json
from datetime import datetime, timedelta
import pytz
import re

# --- 1. CONFIG ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    return ["arizona state", "asu", "maryland", "indiana", "illinois", "iowa", "ucla", "usc", "leeds united", "texas"]

# --- 2. THE STORY ENGINE (AP WIRE DEPTH) ---
def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    # Deep Data Extraction
    def get_stat(team, label):
        try:
            for s in team['statistics']:
                if s['name'] == label: return s['displayValue']
        except: return None
        return None

    def get_lead_athlete(team):
        try: return f"{team['leaders'][0]['leaders'][0]['athlete']['displayName']} ({team['leaders'][0]['leaders'][0]['displayValue']})"
        except: return None

    h_star, a_star = get_lead_athlete(home), get_lead_athlete(away)
    h_fg = get_stat(home, 'fieldGoalPct')
    a_fg = get_stat(away, 'fieldGoalPct')
    
    dateline = f"<b>{city}, {state} -- </b>"

    # --- FINAL RECAP (AP STYLE) ---
    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        w_star = get_lead_athlete(win)
        
        story = f"{dateline} {w_star if w_star else win['team']['displayName']} took control late as {win['team']['displayName']} "
        story += f"secured a {win['score']}-{los['score']} victory over {los['team']['displayName']} at {venue}.<br><br>"
        
        story += f"The {win['team']['shortDisplayName']} dominated the interior, "
        if h_fg and a_fg:
            story += f"shooting a collective {h_fg if win==home else a_fg}% from the floor. "
        
        story += f"{los['team']['displayName']} attempted to rally behind {get_lead_athlete(los) if get_lead_athlete(los) else 'their bench'}, but was unable to close the gap in the final minutes. "
        story += f"The win moves {win['team']['shortDisplayName']} to {win.get('records',[{}])[0].get('summary','0-0')} on the season.<br><br>"
        
        story += f"<b>UP NEXT:</b> {home['team']['shortDisplayName']} is scheduled {get_up_next(home['team']['id'], sport, league)}, while {away['team']['shortDisplayName']} will prepare {get_up_next(away['team']['id'], sport, league)}."
        return story

    # --- LIVE REPORT ---
    if status_type == "STATUS_IN_PROGRESS":
        clock = event['status']['type']['detail']
        leading = home if int(home['score']) > int(away['score']) else away
        diff = abs(int(home['score']) - int(away['score']))
        
        story = f"{dateline} The {leading['team']['shortDisplayName']} are currently maintaining a {diff}-point lead over {away['team']['shortDisplayName'] if leading==home else home['team']['shortDisplayName']} "
        story += f"with {clock} remaining at {venue}.<br><br>"
        story += f"<b>Top Performers:</b> {h_star if h_star else 'N/A'} (Home) and {a_star if a_star else 'N/A'} (Away) have provided the bulk of the offensive production in what has been a physical {sport} contest."
        return story

    return f"{dateline} The {away['team']['displayName']} travel to {city} for a high-stakes matchup against {home['team']['displayName']}. Kickoff is set for {get_live_weather(city)} conditions."

# --- 3. THE BROADCAST SCOREBUG (HTML/CSS) ---
def generate_html(games):
    html = f"""<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Roboto:wght@400;900&display=swap');
    body {{ background: #0e1114; color: #fff; font-family: 'Roboto', sans-serif; padding: 40px; }}
    .container {{ max-width: 900px; margin: auto; }}
    
    /* SCOREBUG DESIGN */
    .scorebug {{ 
        display: flex; background: #1a1d23; border-bottom: 4px solid #ffc627; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.5); overflow: hidden; height: 70px; align-items: stretch;
    }}
    .sb-status {{ background: #000; color: #ffc627; padding: 0 20px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 1.1em; text-transform: uppercase; min-width: 120px; justify-content: center; }}
    .sb-team {{ display: flex; align-items: center; padding: 0 20px; flex: 1; gap: 15px; font-weight: 900; font-size: 1.4em; }}
    .sb-team img {{ height: 40px; width: 40px; object-fit: contain; }}
    .sb-score {{ background: #2a2e35; width: 80px; display: flex; align-items: center; justify-content: center; font-size: 2.2em; font-weight: 900; border-left: 1px solid #3d424a; }}
    .sb-vs {{ background: #111; width: 40px; display: flex; align-items: center; justify-content: center; font-size: 0.8em; color: #666; }}

    /* STORY DESIGN */
    .wire-container {{ background: #fdfdfd; color: #111; padding: 35px; margin-bottom: 50px; border-radius: 0 0 4px 4px; line-height: 1.8; font-size: 1.1em; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
    .wire-header {{ font-family: 'Oswald'; text-transform: uppercase; border-bottom: 2px solid #111; margin-bottom: 15px; display: flex; justify-content: space-between; }}
    </style></head><body><div class="container">"""

    for g in games:
        html += f"""
        <div class="scorebug">
            <div class="sb-status">{g['status_text']}</div>
            <div class="sb-team" style="justify-content: flex-end;">{g['away_name']} <img src="{g['away_logo']}"></div>
            <div class="sb-score">{g['away_score']}</div>
            <div class="sb-vs">VS</div>
            <div class="sb-score">{g['home_score']}</div>
            <div class="sb-team"><img src="{g['home_logo']}"> {g['home_name']}</div>
        </div>
        <div class="wire-container">
            <div class="wire-header"><span>ESPN SPORTS WIRE</span><span>{g['headline'].split(' ')[0]}</span></div>
            {g['story']}
        </div>"""
    
    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

# --- [REST OF FETCHING LOGIC FROM PREVIOUS SCRIPT REMAINS SAME] ---
