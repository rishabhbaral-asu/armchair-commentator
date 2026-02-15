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
        "arizona state", "asu", "iowa", "nebraska", "santa clara", "portland", 
        "utep", "suns", "49ers", "lakers", "warriors", "mercury"
    ]

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "100", "groups": "50" if "college" in league else "80", "cb": int(time.time())}
    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = str(event['id'])
            if eid in seen_ids or not any(re.search(r'\b' + re.escape(t) + r'\b', event.get("name", "").lower()) for t in whitelist):
                continue
            
            # Fetch deeper summary for REAL headlines
            sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
            s_data = requests.get(sum_url).json()
            
            headline = "LIVE WIRE — Game coverage in progress."
            news = s_data.get("news", {}).get("articles", [])
            if news:
                headline = news[0].get("headline", news[0].get("description", ""))
            elif event["status"]["type"]["state"] == "post":
                comp = event["competitions"][0]
                winner = next(t for t in comp["competitors"] if t.get("winner"))
                headline = f"FINAL: {winner['team']['displayName']} captures the victory."

            comp = event["competitions"][0]
            games.append({
                "id": eid,
                "category": "college" if "college" in league else "pro",
                "sport_type": sport.upper(),
                "league": league.upper().replace("-", " "),
                "status": event["status"]["type"]["state"],
                "home": {"name": comp['competitors'][0]['team']['shortDisplayName'], "score": comp['competitors'][0].get("score", "0")},
                "away": {"name": comp['competitors'][1]['team']['shortDisplayName'], "score": comp['competitors'][1].get("score", "0")},
                "headline": headline,
                "date": event["date"]
            })
            seen_ids.add(eid)
    except: pass
    return games

def generate_html(games):
    az_tz = pytz.timezone('America/Phoenix')
    now_str = datetime.now(az_tz).strftime("%A, %B %d, %Y")
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>TEMPE TORCH | Sports Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Oswald:wght@500;700&family=Inter:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {{ --gold: #FFC627; --maroon: #8C1D40; --dark: #0A0A0A; --card: #161616; }}
            body {{ background: var(--dark); color: #fff; font-family: 'Inter', sans-serif; margin: 0; }}
            
            /* Header & Clock */
            header {{ background: #000; padding: 40px 20px; border-bottom: 4px solid var(--maroon); text-align: center; }}
            h1 {{ font-family: 'UnifrakturMaguntia', serif; font-size: 5.5rem; color: var(--gold); margin: 0; line-height: 1; }}
            .clocks {{ font-family: 'Oswald', sans-serif; margin-top: 10px; color: #aaa; letter-spacing: 2px; }}
            #master-clock {{ color: var(--gold); font-weight: 700; }}

            /* Filter Tabs */
            .filter-bar {{ display: flex; justify-content: center; gap: 20px; margin: 30px 0; }}
            .filter-btn {{ background: transparent; border: 1px solid #333; color: #888; padding: 10px 25px; cursor: pointer; font-family: 'Oswald'; text-transform: uppercase; transition: 0.3s; }}
            .filter-btn.active, .filter-btn:hover {{ border-color: var(--gold); color: var(--gold); background: #111; }}

            /* Grid */
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; padding: 0 40px 40px; }}
            .card {{ background: var(--card); border: 1px solid #222; padding: 30px; position: relative; transition: 0.3s; }}
            .card:hover {{ transform: scale(1.02); border-color: var(--maroon); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            
            .meta {{ font-size: 0.7rem; font-weight: 900; color: var(--maroon); letter-spacing: 3px; text-transform: uppercase; margin-bottom: 15px; }}
            .headline {{ font-family: 'Oswald', sans-serif; font-size: 1.3rem; line-height: 1.2; margin-bottom: 20px; color: #fff; height: 3.2em; overflow: hidden; }}
            
            .score-box {{ display: flex; justify-content: space-between; align-items: center; background: #000; padding: 15px; border-radius: 4px; }}
            .team-col {{ display: flex; flex-direction: column; }}
            .team-name {{ font-family: 'Oswald', sans-serif; font-size: 1.6rem; }}
            .score-val {{ font-family: 'Oswald', sans-serif; font-size: 2.2rem; color: var(--gold); }}
            
            .status-footer {{ margin-top: 15px; font-size: 0.8rem; font-weight: bold; display: flex; justify-content: space-between; }}
            .live-dot {{ color: #ff4d4d; animation: blink 1s infinite; }}
            @keyframes blink {{ 50% {{ opacity: 0; }} }}
        </style>
    </head>
    <body>
        <header>
            <h1>The Tempe Torch</h1>
            <div class="clocks">{now_str} | <span id="master-clock">--:--:--</span> MST</div>
        </header>

        <div class="filter-bar">
            <button class="filter-btn active" onclick="filterGames('all', this)">All Feeds</button>
            <button class="filter-btn" onclick="filterGames('college', this)">College</button>
            <button class="filter-btn" onclick="filterGames('pro', this)">Professional</button>
        </div>

        <div class="grid" id="main-grid"></div>

        <script>
            const games = {json.dumps(games)};
            
            function filterGames(cat, btn) {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                render(cat);
            }}

            function render(filter = 'all') {{
                const grid = document.getElementById('main-grid');
                grid.innerHTML = '';
                const filtered = filter === 'all' ? games : games.filter(g => g.category === filter);
                
                filtered.forEach(g => {{
                    const card = document.createElement('div');
                    card.className = 'card';
                    let statusTxt = g.status === 'pre' ? `<span id="t-${{g.id}}" style="color:var(--gold)">--:--:--</span>` : 
                                    g.status === 'in' ? '<span class="live-dot">● LIVE</span>' : 'FINAL';
                    
                    card.innerHTML = `
                        <div class="meta">${{g.league}} // ${{g.sport_type}}</div>
                        <div class="headline">${{g.headline}}</div>
                        <div class="score-box">
                            <div class="team-col"><span class="team-name">${{g.away.name}}</span><span class="team-name">${{g.home.name}}</span></div>
                            <div class="team-col" style="text-align:right"><span class="score-val">${{g.away.score}}</span><span class="score-val">${{g.home.score}}</span></div>
                        </div>
                        <div class="status-footer"><span>STATUS</span><span>${{statusTxt}}</span></div>
                    `;
                    grid.appendChild(card);
                }});
            }}

            function update() {{
                const now = new Date();
                document.getElementById('master-clock').innerText = now.toLocaleTimeString('en-US', {{hour12:false, timeZone:'America/Phoenix'}});
                games.forEach(g => {{
                    const el = document.getElementById('t-' + g.id);
                    if(el) {{
                        const diff = new Date(g.date) - now;
                        if(diff > 0) {{
                            const h = Math.floor(diff/3600000), m = Math.floor((diff%3600000)/60000), s = Math.floor((diff%60000)/1000);
                            el.innerText = `T-MINUS ${{h}}h ${{m}}m ${{s}}s`;
                        }} else {{ el.innerText = "STARTING"; }}
                    }}
                }});
            }}

            setInterval(update, 1000);
            render(); update();
        </script>
    </body>
    </html>
    """

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
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
