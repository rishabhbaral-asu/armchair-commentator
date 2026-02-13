import requests
import json
from datetime import datetime, timedelta
import os
import re
from googlesearch import search # Ensure this is in your requirements or install via pip

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
OUTPUT_FILE = "index.html"
DAYS_BACK = 3    # Now catching more completed games
DAYS_AHEAD = 4   # Previews for upcoming games
# ---------------------

def load_whitelist():
    paths = [WHITELIST_FILE, os.path.join("..", WHITELIST_FILE), "scripts/" + WHITELIST_FILE]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                return [line.strip().lower() for line in f if line.strip()]
    return []

def is_match(text, whitelist):
    if not text: return False
    text_clean = text.lower()
    for item in whitelist:
        if re.search(r'\b' + re.escape(item) + r'\b', text_clean):
            return True
    return False

def get_game_story(sport, league, game_id):
    """Fetches the full AP-Style Recap or Preview from ESPN."""
    summary_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    try:
        data = requests.get(summary_url, timeout=5).json()
        # Try Recap first (for finished games), then Preview
        story = data.get("news", {}).get("articles", [{}])[0]
        content = story.get("story", story.get("description", "No detailed analysis available yet."))
        # Clean up HTML tags if any
        clean_content = re.sub('<[^<]+?>', '', content)
        return clean_content[:2000] + "..." if len(clean_content) > 2000 else clean_content
    except:
        return "Analysis pending for this matchup."

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "100", "dates": f"{(datetime.now()-timedelta(days=DAYS_BACK)).strftime('%Y%m%d')}-{(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime('%Y%m%d')}"}
    
    print(f"   Gathering {league} reports...")
    games = []
    try:
        data = requests.get(url, params=params).json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                comp = event["competitions"][0]
                home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                
                # GET THE STORY
                print(f"      Writing story for {event.get('name')}...")
                story = get_game_story(sport, league, event['id'])

                games.append({
                    "sport": league.upper().replace(".1","").replace("COLLEGE-","NCAA "),
                    "status": event["status"]["type"]["state"],
                    "status_detail": event["status"]["type"]["detail"],
                    "home_name": home["team"]["displayName"],
                    "home_logo": home["team"].get("logo", ""),
                    "home_score": home.get("score", "0"),
                    "away_name": away["team"]["displayName"],
                    "away_logo": away["team"].get("logo", ""),
                    "away_score": away.get("score", "0"),
                    "story": story,
                    "raw_utc": event.get("date")
                })
        return games
    except: return []

def get_cricket_google(whitelist):
    """Fallback: Searches Google for live scores of whitelisted cricket teams."""
    print("   Searching Google for Cricket Scores...")
    cricket_results = []
    for team in whitelist:
        # We only search teams that are likely cricket nations or in your list
        # Simple heuristic to avoid over-searching
        query = f"{team} cricket score today"
        try:
            # Note: Scrapers for Google are fragile, this is a basic capture
            # In a real CI environment, you'd use a SERP API
            print(f"      Checking status: {team}...")
            # For this MVP, we create a 'pseudo-story' from the top search snippet
            # or just log that we are looking. 
            # (Actual scraping of Google SERP requires specialized libraries)
            pass 
        except: pass
    return cricket_results

def generate_html(games):
    games_json = json.dumps(games)
    # The HTML uses the same logic as before but adds a "Read Story" section
    # and a scrollable text area for the AP-style content.
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Tempe Torch Newsroom</title>
        <style>
            :root {{ --bg: #0a0a0a; --card: #161616; --accent: #d32f2f; --text: #f0f0f0; }}
            body {{ font-family: 'Georgia', serif; background: var(--bg); color: var(--text); padding: 20px; }}
            .top-bar {{ border-bottom: 4px double #444; text-align: center; padding-bottom: 20px; margin-bottom: 30px; }}
            .top-bar h1 {{ font-size: 3rem; margin: 0; font-variant: small-caps; }}
            .grid {{ max-width: 1000px; margin: auto; }}
            .article {{ background: var(--card); border: 1px solid #333; padding: 25px; margin-bottom: 40px; border-radius: 4px; }}
            .meta {{ color: var(--accent); font-weight: bold; text-transform: uppercase; font-family: sans-serif; font-size: 0.8rem; }}
            .headline {{ font-size: 2rem; margin: 10px 0; line-height: 1.1; }}
            .scoreboard {{ display: flex; align-items: center; background: #000; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            .team-box {{ flex: 1; text-align: center; }}
            .logo-circ {{ width: 50px; height: 50px; background: #fff; border-radius: 50%; padding: 5px; margin: auto; }}
            .score-val {{ font-size: 2rem; font-family: sans-serif; font-weight: 900; }}
            .story-content {{ line-height: 1.6; color: #ccc; font-size: 1.1rem; border-top: 1px solid #333; padding-top: 15px; white-space: pre-wrap; }}
            .status-line {{ font-family: sans-serif; background: #222; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <h1>The Tempe Torch Gazette</h1>
            <p>Arizona's Definitive Sports Record • <span id="clock"></span></p>
        </div>
        <div id="news-feed" class="grid"></div>

        <script>
            const games = {games_json};
            const feed = document.getElementById('news-feed');
            
            games.forEach(g => {{
                const art = document.createElement('div');
                art.className = 'article';
                art.innerHTML = `
                    <div class="meta">${{g.sport}} • ${{new Date(g.raw_utc).toLocaleString('en-US', {{timeZone: 'America/Phoenix'}})}}</div>
                    <div class="headline">${{g.away_name}} at ${{g.home_name}}</div>
                    <div class="status-line">${{g.status_detail}}</div>
                    <div class="scoreboard">
                        <div class="team-box">
                            <div class="logo-circ"><img src="${{g.away_logo}}" style="width:100%"></div>
                            <div>${{g.away_name}}</div>
                            <div class="score-val">${{g.away_score}}</div>
                        </div>
                        <div style="font-size: 1.5rem; color: #444;">VS</div>
                        <div class="team-box">
                            <div class="logo-circ"><img src="${{g.home_logo}}" style="width:100%"></div>
                            <div>${{g.home_name}}</div>
                            <div class="score-val">${{g.home_score}}</div>
                        </div>
                    </div>
                    <div class="story-content"><strong>ANALYSIS:</strong><br>${{g.story}}</div>
                `;
                feed.appendChild(art);
            }});
        </script>
    </body>
    </html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    
    # Standard Sources
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl"), ("baseball", "mlb"),
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), 
        ("baseball", "college-baseball"), ("softball", "college-softball"),
        ("soccer", "eng.1"), ("soccer", "eng.2"), ("soccer", "ita.1")
    ]
    
    for sport, league in sources:
        all_games.extend(get_espn_data(sport, league, whitelist))
    
    # Write
    html = generate_html(all_games)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print("Gazette Updated.")

if __name__ == "__main__":
    main()
