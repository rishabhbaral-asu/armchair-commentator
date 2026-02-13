import requests
import json
from datetime import datetime, timedelta
import os
import re

# --- CONFIGURATION ---
WHITELIST_FILE = "scripts/whitelist.txt"
OUTPUT_FILE = "index.html"
DAYS_BACK = 5    # Catch everything from the last 5 days
DAYS_AHEAD = 3   # Previews for the next 3 days
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
        articles = data.get("news", {}).get("articles", [])
        if not articles:
            return "No detailed analysis available for this matchup at this time."
        
        story = articles[0]
        content = story.get("story", story.get("description", "Analysis pending."))
        # Clean HTML tags
        clean_content = re.sub('<[^<]+?>', '', content)
        return clean_content
    except:
        return "The newsroom is currently processing data for this event."

def get_espn_data(sport, league, whitelist):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    date_str = f"{(datetime.now()-timedelta(days=DAYS_BACK)).strftime('%Y%m%d')}-{(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime('%Y%m%d')}"
    params = {"limit": "200", "dates": date_str}
    
    print(f"🗞️  Filing reports for {league}...")
    games = []
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        for event in data.get("events", []):
            if is_match(event.get("name", ""), whitelist):
                comp = event["competitions"][0]
                home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                
                # GET THE FULL STORY
                story = get_game_story(sport, league, event['id'])

                games.append({
                    "sport": league.upper().replace(".1","").replace("MENS-","").replace("COLLEGE-","NCAA "),
                    "status": event["status"]["type"]["state"], # pre, in, post
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
    except Exception as e:
        print(f"Error in {league}: {e}")
        return []

def generate_html(games):
    games_json = json.dumps(games)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tempe Torch Newsroom</title>
        <style>
            :root {{ --bg: #fdfcf0; --ink: #1a1a1b; --accent: #8b0000; --border: #333; }}
            body {{ font-family: 'Times New Roman', Times, serif; background: var(--bg); color: var(--ink); margin: 0; padding: 0; }}
            
            /* Header Section */
            header {{ text-align: center; border-bottom: 5px double var(--ink); padding: 40px 20px; margin: 0 40px; }}
            header h1 {{ font-size: 4rem; margin: 0; text-transform: uppercase; letter-spacing: -2px; }}
            .masthead-meta {{ font-family: sans-serif; font-weight: bold; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); padding: 5px 0; margin-top: 10px; display: flex; justify-content: space-between; }}

            /* Content Container */
            .container {{ max-width: 900px; margin: 40px auto; padding: 0 20px; }}
            
            /* Section Styling */
            .section-title {{ font-family: sans-serif; border-bottom: 2px solid var(--ink); text-transform: uppercase; margin-bottom: 30px; font-size: 1.2rem; }}

            /* Article Styling */
            article {{ margin-bottom: 80px; }}
            .category {{ font-family: sans-serif; color: var(--accent); font-weight: bold; font-size: 0.9rem; text-transform: uppercase; }}
            .headline {{ font-size: 2.5rem; line-height: 1; margin: 10px 0; font-weight: bold; }}
            .dateline {{ font-family: sans-serif; font-size: 0.8rem; color: #555; margin-bottom: 20px; }}
            
            /* Clean Scoreboard */
            .scoreboard {{ display: flex; align-items: center; border-top: 1px solid #ccc; border-bottom: 1px solid #ccc; padding: 20px 0; margin: 20px 0; }}
            .team {{ flex: 1; text-align: center; }}
            .logo-wrap {{ width: 60px; height: 60px; background: #fff; border-radius: 50%; border: 1px solid #ddd; padding: 5px; margin: 0 auto 10px; }}
            .logo-wrap img {{ width: 100%; height: 100%; object-fit: contain; }}
            .score {{ font-size: 2.5rem; font-family: sans-serif; font-weight: bold; }}
            .vs-text {{ font-family: sans-serif; font-style: italic; color: #999; padding: 0 20px; }}

            /* Story Content */
            .story {{ line-height: 1.6; font-size: 1.2rem; text-align: justify; column-count: 1; }}
            @media (min-width: 768px) {{ .story {{ column-count: 2; column-gap: 40px; }} }}
            .story::first-letter {{ float: left; font-size: 4rem; line-height: 0.8; padding-top: 4px; padding-right: 8px; font-weight: bold; }}

            footer {{ text-align: center; padding: 40px; border-top: 1px solid #ccc; font-family: sans-serif; font-size: 0.8rem; }}
        </style>
    </head>
    <body>

    <header>
        <h1>The Tempe Torch</h1>
        <div class="masthead-meta">
            <span>VOL. CXIV... NO. 36,210</span>
            <span id="az-clock">TEMPE, ARIZONA</span>
            <span>$0.50</span>
        </div>
    </header>

    <div class="container" id="news-feed">
        </div>

    <footer>
        &copy; 2026 THE TEMPE TORCH PRESS • REPRODUCTION WITHOUT PERMISSION IS PROHIBITED
    </footer>

    <script>
        const games = {games_json};
        const feed = document.getElementById('news-feed');

        // Clock logic
        const azTime = new Intl.DateTimeFormat('en-US', {{
            timeZone: 'America/Phoenix',
            weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
        }}).format(new Date());
        document.getElementById('az-clock').innerText = azTime.toUpperCase();

        // Sort: Live first, then newest
        games.sort((a, b) => new Date(b.raw_utc) - new Date(a.raw_utc));

        games.forEach(g => {{
            const storyNode = document.createElement('article');
            
            storyNode.innerHTML = `
                <div class="category">${{g.sport}} • ${{g.status_detail}}</div>
                <div class="headline">${{g.away_name}} Face ${{g.home_name}} in Key Matchup</div>
                <div class="dateline">BY ASSOCIATED PRESS • ${{new Date(g.raw_utc).toLocaleTimeString('en-US', {{timeZone: 'America/Phoenix', hour:'2-digit', minute:'2-digit'}})}} AZT</div>
                
                <div class="scoreboard">
                    <div class="team">
                        <div class="logo-wrap"><img src="${{g.away_logo}}"></div>
                        <div style="font-family:sans-serif; font-weight:bold;">${{g.away_name}}</div>
                        <div class="score">${{g.away_score}}</div>
                    </div>
                    <div class="vs-text">at</div>
                    <div class="team">
                        <div class="logo-wrap"><img src="${{g.home_logo}}"></div>
                        <div style="font-family:sans-serif; font-weight:bold;">${{g.home_name}}</div>
                        <div class="score">${{g.home_score}}</div>
                    </div>
                </div>

                <div class="story">${{g.story}}</div>
            `;
            feed.appendChild(storyNode);
        }});

        if(games.length === 0) {{
            feed.innerHTML = "<p style='text-align:center; font-style:italic;'>No dispatches from the field today.</p>";
        }}
    </script>
    </body>
    </html>
    """

def main():
    whitelist = load_whitelist()
    all_games = []
    
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl"), ("baseball", "mlb"),
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), 
        ("baseball", "college-baseball"), ("softball", "college-softball"),
        ("soccer", "eng.1"), ("soccer", "eng.2"), ("soccer", "eng.3"),
        ("soccer", "ita.1"), ("soccer", "ger.1"), ("soccer", "esp.1")
    ]
    
    for sport, league in sources:
        all_games.extend(get_espn_data(sport, league, whitelist))
    
    html = generate_html(all_games)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print("Gazette Publication Complete.")

if __name__ == "__main__":
    main()
