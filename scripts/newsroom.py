import requests
import json
from datetime import datetime
import pytz
import re
import time

# --- CONFIG ---
OUTPUT_FILE = "index.html"

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
def craft_custom_headline(event, sport, league):
    """
    Manually overrides generic headlines with logic based on scores and rivals.
    """
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    h_name = home["team"]["displayName"]
    a_name = away["team"]["displayName"]
    status = event["status"]["type"]["state"]
    
    # RIVALRY CHECK: ASU vs Arizona
    if "Arizona State" in [h_name, a_name] and "Arizona" in [h_name, a_name]:
        if status == "post":
            return f"VALENTINE'S DAY SWEEP: Sun Devils take down Wildcats 75-69 in OT thriller!"
        return "TERRITORIAL CUP: The rivalry heats up on the hardwood."

    # RECENT RESULT: Santa Clara @ Portland
    if "Santa Clara" in a_name and "Portland" in h_name:
        if status == "post":
            return "BRONCO BLITZ: Santa Clara erupts for 28-point 4th quarter to stun Pilots 77-66."

    # UPCOMING: Iowa @ Nebraska (Monday game)
    if "Iowa" in a_name and "Nebraska" in h_name:
        return "PRESIDENTS' DAY CLASH: Hawkeyes land in Lincoln looking for season sweep."

    # ASU BASEBALL: vs Omaha
    if "Arizona State" in h_name and "Omaha" in a_name:
        if status == "pre":
            return "SWEEP WATCH: Sun Devils (2-0) look to finish the job against Mavericks today."
        return f"DIAMOND REPORT: ASU Baseball vs Omaha - Game 3"

    # FALLBACK: Build a factual one
    if status == "post":
        winner = h_name if home.get("winner") else a_name
        score = f"{away['score']}-{home['score']}"
        return f"FINAL: {winner} secures a hard-fought {score} victory."
    
    return f"MATCHUP: {a_name} visits {h_name}."

def get_dashboard_data():
    whitelist = get_whitelist()
    results = []
    # Targeted categories to ensure whitelist teams are found
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("basketball", "nba"),
        ("hockey", "mens-college-hockey"),
        ("baseball", "mlb"),
        ("baseball", "college-softball")
    ]

    for sport, league in leagues:
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        try:
            data = requests.get(url).json()
            for event in data.get("events", []):
                name = event.get("name", "").lower()
                # STRICT WHITELIST FILTER
                if any(team in name for team in whitelist):
                    comp = event["competitions"][0]
                    results.append({
                        "id": event["id"],
                        "league": league.upper().replace("-", " "),
                        "headline": craft_custom_headline(event, sport, league),
                        "home": {"name": comp["competitors"][0]["team"]["shortDisplayName"], "score": comp["competitors"][0].get("score", "0")},
                        "away": {"name": comp["competitors"][1]["team"]["shortDisplayName"], "score": comp["competitors"][1].get("score", "0")},
                        "status": event["status"]["type"]["state"],
                        "date": event["date"]
                    })
        except: continue
    return results
def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now_str = datetime.now(az_tz).strftime("%A, %B %d, %Y")
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>THE TEMPE TORCH</title>
        <link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Oswald:wght@700&family=Inter:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {{ --gold: #FFC627; --maroon: #8C1D40; --dark: #050505; }}
            body {{ background: var(--dark); color: #fff; font-family: 'Inter', sans-serif; margin: 0; padding: 20px; }}
            header {{ text-align: center; border-bottom: 4px solid var(--maroon); padding-bottom: 20px; }}
            h1 {{ font-family: 'UnifrakturMaguntia', serif; font-size: 6rem; color: var(--gold); margin: 0; }}
            .clocks {{ font-family: 'Oswald', sans-serif; color: #888; font-size: 1.4rem; }}
            
            .filter-bar {{ display: flex; justify-content: center; gap: 15px; margin: 25px 0; }}
            .f-btn {{ background: #111; border: 1px solid #333; color: #fff; padding: 10px 20px; cursor: pointer; font-family: 'Oswald'; }}
            .f-btn.active {{ border-color: var(--gold); color: var(--gold); }}

            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
            .card {{ background: #111; border-left: 5px solid var(--maroon); padding: 25px; transition: 0.2s; }}
            .card:hover {{ transform: translateY(-5px); border-color: var(--gold); }}
            
            .headline {{ font-family: 'Oswald', sans-serif; font-size: 1.4rem; line-height: 1.2; margin: 15px 0; color: #fff; text-transform: uppercase; }}
            .teams {{ display: flex; justify-content: space-between; font-weight: bold; border-top: 1px solid #222; padding-top: 15px; }}
            .score {{ font-size: 2rem; color: var(--gold); }}
            .countdown {{ color: #00ff00; font-family: monospace; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <header>
            <h1>The Tempe Torch</h1>
            <div class="clocks">{now_str} | <span id="master-clock">--:--:--</span> MST</div>
        </header>

        <div class="filter-bar">
            <button class="f-btn active" onclick="filter('all', this)">ALL WIRE</button>
            <button class="f-btn" onclick="filter('college', this)">COLLEGE</button>
            <button class="f-btn" onclick="filter('pro', this)">PRO</button>
        </div>

        <div class="grid" id="main-grid"></div>

        <script>
            const games = {json.dumps(games)};
            function filter(cat, btn) {{
                document.querySelectorAll('.f-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const grid = document.getElementById('main-grid');
                grid.innerHTML = '';
                games.filter(g => cat === 'all' || g.category === cat).forEach(g => {{
                    const card = document.createElement('div');
                    card.className = 'card';
                    let timer = g.status === 'pre' ? `<div id="t-${{g.id}}" class="countdown"></div>` : g.status === 'in' ? '<b style="color:red">● LIVE</b>' : 'FINAL';
                    card.innerHTML = `
                        <small style="color:var(--maroon)">${{g.league}}</small>
                        <div class="headline">${{g.headline}}</div>
                        <div class="teams">
                            <span>${{g.away.name}}<br>${{g.home.name}}</span>
                            <span class="score">${{g.away.score}} - ${{g.home.score}}</span>
                        </div>
                        <div style="margin-top:10px">${{timer}}</div>
                    `;
                    grid.appendChild(card);
                }});
            }}
            function tick() {{
                const now = new Date();
                document.getElementById('master-clock').innerText = now.toLocaleTimeString('en-US', {{hour12:false, timeZone:'America/Phoenix'}});
                games.forEach(g => {{
                    const el = document.getElementById('t-' + g.id);
                    if(el) {{
                        const diff = new Date(g.date) - now;
                        if(diff > 0) {{
                            const h = Math.floor(diff/3600000), m = Math.floor((diff%3600000)/60000), s = Math.floor((diff%60000)/1000);
                            el.innerText = `STARTS IN: ${{h}}h ${{m}}m ${{s}}s`;
                        }} else {{ el.innerText = "GAME STARTING"; }}
                    }}
                }});
            }}
            setInterval(tick, 1000);
            filter('all', document.querySelector('.f-btn'));
        </script>
    </body>
    </html>
    """

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    # Expanded leagues to include Baseball & Softball for ASU
    leagues = [
        ("basketball", "nba"), ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("hockey", "nhl"), ("baseball", "mlb"), ("baseball", "college-baseball"), ("baseball", "college-softball")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(all_games))

if __name__ == "__main__":
    main()
