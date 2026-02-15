import requests
import json
from datetime import datetime
import pytz
import re

# --- 1. THE WHITELIST ---
def get_whitelist():
    return [
        "san francisco 49ers", "ac milan", "angel city", "anaheim angels", "arizona state", "asu", 
        "athletics", "atletico madrid", "austin fc", "bakersfield", "california", "cal poly", 
        "capitals", "arizona cardinals", "cal baptist", "la chargers", "chelsea", "la clippers", 
        "commanders", "coventry city", "dallas cowboys", "crystal palace", "arizona diamondbacks", 
        "dc united", "fc dallas", "houston dash", "la dodgers", "anaheim ducks", "east texas a&m", 
        "fresno state", "fulham", "fullerton", "san francisco giants", "new york giants", "gcu", 
        "houston dynamo", "juventus", "sacramento kings", "la kings", "la galaxy", "lafc", "india", 
        "la lakers", "united states", "lbsu", "leeds united", "leverkusen", "lyon", "m'gladbach", 
        "mainz", "marseille", "maryland", "dallas mavericks", "phoenix mercury", "phoenix suns", 
        "inter miami", "as monaco", "mystics", "washington nationals", "north texas", "norwich", 
        "nott'm forest", "orioles", "san diego padres", "parma", "psv", "la rams", "texas rangers", 
        "baltimore ravens", "saint mary's", "san diego", "san jose", "santa clara", "san jose sharks", 
        "la sparks", "washington spirit", "st. pauli", "dallas stars", "texas", "tolouse", "uc davis", 
        "uc irvine", "ucla", "usc", "uc riverside", "uc san diego", "ucsb", "utep", "valkyries", 
        "venezia", "golden state warriors", "san diego wave", "dallas wings", "wizards", "wrexham", 
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium"
    ]
# --- 2. THE STORYMAKER (Your Custom Headlines) ---
def craft_custom_headline(event):
    comp = event["competitions"][0]
    h_name = comp["competitors"][0]["team"]["displayName"]
    a_name = away_name = comp["competitors"][1]["team"]["displayName"]
    status = event["status"]["type"]["state"]
    
    # RIVALRY: ASU vs Arizona (Feb 14 Recap)
    if "Arizona State" in [h_name, a_name] and "Arizona" in [h_name, a_name]:
        return "VALENTINE'S DAY SWEEP: Sun Devils take down Wildcats 75-69 in OT thriller!"

    # RECAP: Santa Clara @ Portland (Feb 14 Recap)
    if "Santa Clara" in a_name and "Portland" in h_name:
        return "BRONCO BLITZ: Santa Clara erupts for 28-point 4th quarter to stun Pilots 77-66."

    # UPCOMING: Iowa @ Nebraska (Feb 16 Game)
    if "Iowa" in a_name and "Nebraska" in h_name:
        return "PRESIDENTS' DAY CLASH: Hawkeyes land in Lincoln looking for season sweep."

    # BASEBALL: ASU vs Omaha (Feb 15 Series Finale)
    if "Arizona State" in h_name and "Omaha" in a_name:
        return "SWEEP WATCH: Sun Devils (2-0) look to finish the series today in Tempe."

    # DEFAULT FALLBACK
    if status == "post":
        winner = h_name if comp["competitors"][0].get("winner") else a_name
        return f"FINAL: {winner} secures a hard-fought victory."
    return f"MATCHUP: {a_name} visits {h_name}."

# --- 3. THE DATA FETCH (Fixed the NameError) ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            
            # Use whitelist to block generic games (like Nicholls State)
            if any(team in name for team in whitelist) and eid not in seen_ids:
                comp = event["competitions"][0]
                results.append({
                    "id": eid,
                    "league": league.upper().replace("-", " "),
                    "headline": craft_custom_headline(event),
                    "home": {"name": comp["competitors"][0]["team"]["shortDisplayName"], "score": comp["competitors"][0].get("score", "0")},
                    "away": {"name": comp["competitors"][1]["team"]["shortDisplayName"], "score": comp["competitors"][1].get("score", "0")},
                    "status": event["status"]["type"]["state"],
                    "date": event["date"]
                })
                seen_ids.add(eid)
    except: pass
    return results

def generate_html(games):
    """
    Takes the list of processed games and writes them into a 
    clean, mobile-friendly index.html file.
    """
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %I:%M %p")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>The Armchair Commentator</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: auto; }}
            .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
            .timestamp {{ font-size: 0.8em; color: #888; }}
            .game-card {{ background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 5px solid #ffc627; }} /* ASU Gold */
            .headline {{ font-weight: bold; font-size: 1.2em; color: #fff; margin-bottom: 8px; }}
            .score-line {{ display: flex; justify-content: space-between; font-size: 1.1em; border-top: 1px solid #333; pt: 8px; mt: 8px; }}
            .league-tag {{ font-size: 0.7em; background: #333; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }}
            .empty-msg {{ text-align: center; padding: 50px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>The Armchair Commentator</h1>
                <div class="timestamp">Last Updated: {now} MST</div>
            </div>
    """

    if not games:
        html_content += '<div class="empty-msg">The newsroom is quiet. Check back shortly for updates on your whitelisted teams.</div>'
    else:
        for g in games:
            html_content += f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="league-tag">{g['league']}</span>
                    <span style="font-size: 0.8em; color: #888;">{g['status'].upper()}</span>
                </div>
                <div class="headline">{g['headline']}</div>
                <div class="score-line">
                    <span>{g['away']['name']} <strong>{g['away']['score']}</strong></span>
                    <span>vs</span>
                    <span><strong>{g['home']['score']}</strong> {g['home']['name']}</span>
                </div>
            </div>
            """

    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f:
        f.write(html_content)

# --- UPDATED MAIN ---
def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("basketball", "nba"),
        ("baseball", "mlb"),
        ("hockey", "nhl")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))

    # THIS IS THE PART THAT WAS MISSING:
    generate_html(all_games)
    print(f"Success! index.html updated with {len(all_games)} games.")

if __name__ == "__main__":
    main()
