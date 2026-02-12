"""
THE TEMPE TORCH — SUNDAY LONGFORM EDITION
-----------------------------------------
1. FETCH: Scrapes ESPN for games within a +/- 7 day window.
2. WRITE: Generates 600+ word feature stories using procedural templates.
3. PUBLISH: Renders a classic "Broadsheet" HTML layout.
"""

import json
import time
import os
import random
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 30 # Slower refresh for longer stories

# The 7-Day Window
WINDOW_DAYS = 7 

TARGET_CITIES = {"Tempe", "Phoenix", "Glendale", "Scottsdale", "Mesa", "Tucson", "Los Angeles", "Las Vegas", "New York", "Lexington", "College Station"}
TARGET_STATES = {"AZ", "KY", "TX"}
TARGET_KEYWORDS = [
    "Suns", "Cardinals", "Diamondbacks", "Coyotes", "ASU", "Arizona State", "Sun Devils", 
    "Wildcats", "Lakers", "Warriors", "Cowboys", "Chiefs", "Kentucky", "Texas A&M"
]

# --- THE GAME ENGINE (Data Fetching) ---

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def is_within_window(date_str):
    """Checks if game is within +/- 7 days of NOW."""
    if not date_str: return False
    try:
        # ESPN ISO Format: 2024-02-12T19:00Z
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = dt - now
        return abs(delta.days) <= WINDOW_DAYS
    except: return False

def get_venue_ambience(venue_name, sport):
    """Injects flavor text based on the stadium."""
    v = venue_name.lower()
    if "arena" in v or "center" in v:
        return f"The atmosphere inside {venue_name} is expected to be electric, with a sell-out crowd ready to make their presence felt."
    if "stadium" in v or "field" in v:
        return f"It is a perfect day for {sport} at {venue_name}, where the elements may play a factor in today's contest."
    return f"Fans are filing into {venue_name} for what promises to be a pivotal matchup."

# --- THE ROBO-REPORTER (Longform Generator) ---

class LongFormGenerator:
    def __init__(self, g):
        self.g = g
        self.h = g['home']
        self.a = g['away']
        self.sport = g['sport_display']
        
    def write_headline(self):
        headlines = [
            f"PREVIEW: {self.a['name']}, {self.h['name']} Set for Clash at {self.g['venue']}",
            f"Stakes High as {self.h['name']} Host {self.a['name']} in Pivotal {self.sport} Showdown",
            f"Deep Dive: Can {self.h['name']} Defend Home Turf Against {self.a['name']}?",
            f"{self.a['name']} vs. {self.h['name']}: Everything You Need to Know"
        ]
        return random.choice(headlines)

    def para_lede(self):
        # The Hook
        time_display = self.g['date_obj'].strftime("%A, %B %d")
        record_txt = f"({self.h['record']})" if self.h['record'] else ""
        
        return (
            f"<span class='dateline'>{self.g['city'].upper()}</span> — "
            f"The calendar reads {time_display}, but the intensity surrounding this matchup suggests "
            f"something far greater. The {self.h['name']} {record_txt} prepare to welcome the "
            f"{self.a['name']} to {self.g['venue']} in a contest that carries significant implications "
            f"for both programs. With the season's narrative still being written, tonight's chapter promises drama."
        )

    def para_context(self):
        # The "Why it Matters"
        ambience = get_venue_ambience(self.g['venue'], self.sport)
        return (
            f"{ambience} For the {self.h['name']}, this game represents a chance to solidify their standing "
            f"and send a message to the rest of the league. Consistency has been the watchword in practice "
            f"all week. Meanwhile, the visiting {self.a['name']} arrive with intentions of playing spoiler, "
            f"knowing that a road victory in this environment would be a marquee addition to their resume."
        )

    def para_matchup(self):
        # The Tactical Analysis (Procedural)
        if self.h['rank'] < self.a['rank']:
            narrative = f"On paper, the {self.h['name']} (No. {self.h['rank']}) hold the advantage, but games aren't played on paper."
        else:
            narrative = "This appears to be an evenly matched tug-of-war, where execution in the final minutes will likely decide the outcome."
            
        return (
            f"<h4>The Tactical Battle</h4>"
            f"{narrative} Analysts are pointing to the battle in the trenches and perimeter defense as the deciding factors. "
            f"If the {self.h['name']} can control the tempo and limit turnovers, they should be able to dictate the flow of the game. "
            f"However, the {self.a['name']} have shown resilience this season, often finding ways to grind out possessions when their offense stagnates."
        )

    def para_star_power(self):
        # Using the scraped Leaders
        if not self.g['leaders']:
            return "Both teams rely on balanced scoring attacks, with depth being a major strength."
            
        leader_txt = " and ".join(self.g['leaders'])
        return (
            f"<h4>Players to Watch</h4>"
            f"All eyes will be on the stars. {leader_txt} have been instrumental for their respective squads. "
            f"The individual matchup between these playmakers could very well determine the trajectory of the contest. "
            f"Scouts have noted that when these key players get going early, their teams become exponentially harder to defend."
        )

    def para_quotes(self):
        # Simulated Quotes (Safe, generic sports-speak)
        coach_quotes = [
            "\"We know they are a well-coached team,\" said the head coach during media availability. \"We have to execute for 60 minutes.\"",
            "\"It's going to come down to who wants it more,\" sources close to the team emphasized.",
            "\"The preparation has been good, now we just have to go out and play our game.\""
        ]
        return (
            f"<h4>Voices from the Locker Room</h4>"
            f"{random.choice(coach_quotes)} The sentiment in the locker room is one of focused determination. "
            f"Neither side is taking this challenge lightly."
        )

    def para_history(self):
        # The "Last Meeting" or History Note
        note = self.g.get('history_note', "These two franchises have a storied history of close finishes.")
        return (
            f"<h4>Series History</h4>"
            f"{note} Familiarity breeds contempt, and there is no shortage of competitive fire between these two. "
            f"Longtime fans will remember previous battles that went down to the wire."
        )

    def para_prediction(self):
        # The Betting Line / Conclusion
        odds = self.g['odds'] if self.g['odds'] else "Even"
        return (
            f"<h4>The Verdict</h4>"
            f"Vegas has set the line at {odds}. While the pundits may favor the home team slightly due to venue advantage, "
            f"the {self.a['name']} are more than capable of an upset. Expect a physical, hard-fought contest that "
            f"may come down to the final possession. Tip-off is scheduled for {self.g['time_display']}."
        )

    def generate(self):
        return (
            f"{self.para_lede()}<br><br>"
            f"{self.para_context()}<br><br>"
            f"{self.para_matchup()}<br><br>"
            f"{self.para_star_power()}<br><br>"
            f"{self.para_quotes()}<br><br>"
            f"{self.para_history()}<br><br>"
            f"{self.para_prediction()}"
        )

# --- PROCESSING ---

def process_game(e, sport, league):
    c = e['competitions'][0]
    h = next((x for x in c['competitors'] if x['homeAway']=='home'), {})
    a = next((x for x in c['competitors'] if x['homeAway']=='away'), {})
    
    # Leaders extraction
    leaders = []
    if 'leaders' in c:
        for l in c['leaders']:
            if l.get('leaders'):
                p = l['leaders'][0]['athlete']['displayName']
                val = l['leaders'][0]['displayValue']
                leaders.append(f"{p} ({val})")

    # History Note
    hist = "No recent data."
    for n in e.get('notes', []):
        if "series" in n.get('text', '').lower(): hist = n['text']

    game_obj = {
        "id": e['id'],
        "date_obj": datetime.strptime(e['date'], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc),
        "time_display": datetime.fromisoformat(e['date'][:-1]).strftime("%I:%M %p"),
        "venue": c.get('venue', {}).get('fullName', 'Stadium'),
        "city": c.get('venue', {}).get('address', {}).get('city', 'Unknown'),
        "sport_display": league.replace("-", " ").title(),
        "odds": c.get('odds', [{}])[0].get('details', 'N/A'),
        "history_note": hist,
        "leaders": leaders,
        "home": {
            "name": h['team']['displayName'],
            "record": h.get('records', [{}])[0].get('summary', ''),
            "rank": h.get('curatedRank', {}).get('current', 99)
        },
        "away": {
            "name": a['team']['displayName'],
            "record": a.get('records', [{}])[0].get('summary', ''),
            "rank": a.get('curatedRank', {}).get('current', 99)
        }
    }
    return game_obj

def run_newsroom():
    print(f"  -> Polling ESPN Wire ({WINDOW_DAYS} Day Window)...")
    sources = [("basketball", "nba"), ("football", "nfl"), ("football", "college-football"), ("basketball", "mens-college-basketball")]
    
    sections = {} # { "NBA": [stories], "NCAA": [stories] }

    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        data = fetch_json(url)
        if not data: continue
        
        for e in data.get('events', []):
            if not is_within_window(e['date']): continue
            
            # Simple Filter: Rank, City, or Keywords
            full_txt = str(e).lower()
            relevant = False
            
            # 1. Location Match
            v = e['competitions'][0].get('venue', {}).get('address', {})
            if v.get('city') in TARGET_CITIES or v.get('state') in TARGET_STATES: relevant = True
            
            # 2. Keyword Match
            if any(k.lower() in full_txt for k in TARGET_KEYWORDS): relevant = True
            
            # 3. Top 25 Match (NCAA)
            h_rank = e['competitions'][0]['competitors'][0].get('curatedRank', {}).get('current', 99)
            if h_rank <= 25: relevant = True

            if relevant:
                g = process_game(e, sport, league)
                writer = LongFormGenerator(g)
                
                story = {
                    "headline": writer.write_headline(),
                    "body": writer.generate(),
                    "date_display": g['date_obj'].strftime("%b %d"),
                    "category": league.replace("mens-", "").replace("college-", "NCAA ").upper()
                }
                
                if story['category'] not in sections: sections[story['category']] = []
                sections[story['category']].append(story)
                
    return sections

def publish_broadsheet(sections):
    print("  -> Printing Broadsheet...")
    
    main_content = ""
    for cat, stories in sections.items():
        # Sort by date
        stories.sort(key=lambda x: x['date_display'])
        
        articles_html = ""
        for s in stories:
            articles_html += f"""
            <article>
                <div class="article-meta">{cat} • {s['date_display']}</div>
                <h2>{s['headline']}</h2>
                <div class="article-body">
                    {s['body']}
                </div>
                <div class="article-footer">AP WIRE • TEMPE TORCH</div>
            </article>
            <hr class="story-divider">
            """
            
        main_content += f"<section class='desk'><h3>{cat} DESK</h3>{articles_html}</section>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>The Tempe Torch: Sunday Edition</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');
            
            :root {{ --paper: #f9f7f1; --ink: #222; --accent: #8b0000; }}
            
            body {{ 
                background-color: var(--paper); 
                color: var(--ink); 
                font-family: 'Lora', serif; 
                margin: 0; 
                padding: 40px; 
                line-height: 1.6;
            }}
            
            /* MASTHEAD */
            header {{ 
                text-align: center; 
                border-bottom: 4px double var(--ink); 
                padding-bottom: 20px; 
                margin-bottom: 50px; 
            }}
            h1 {{ 
                font-family: 'Playfair Display', serif; 
                font-size: 5rem; 
                margin: 0; 
                text-transform: uppercase; 
                letter-spacing: -2px; 
            }}
            .tagline {{ 
                font-family: 'Lora', serif; 
                font-style: italic; 
                font-size: 1.1rem; 
                margin-top: 10px; 
            }}
            
            /* LAYOUT */
            .desk {{ margin-bottom: 80px; }}
            .desk h3 {{ 
                font-family: 'Playfair Display'; 
                font-size: 2rem; 
                border-bottom: 2px solid var(--accent); 
                display: inline-block; 
                margin-bottom: 30px; 
            }}
            
            article {{ 
                max-width: 800px; 
                margin: 0 auto 60px auto; 
            }}
            
            h2 {{ 
                font-family: 'Playfair Display'; 
                font-size: 2.5rem; 
                line-height: 1.1; 
                margin-bottom: 20px; 
            }}
            
            .article-meta {{ 
                font-family: sans-serif; 
                font-size: 0.8rem; 
                font-weight: bold; 
                color: var(--accent); 
                margin-bottom: 10px; 
                text-transform: uppercase; 
                letter-spacing: 1px; 
            }}
            
            .article-body {{ 
                font-size: 1.15rem; 
                text-align: justify; 
            }}
            
            .article-body h4 {{
                font-family: sans-serif;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #555;
                margin-top: 30px;
                margin-bottom: 5px;
                border-bottom: 1px solid #ddd;
            }}
            
            .dateline {{ 
                font-weight: bold; 
                text-transform: uppercase; 
            }}
            
            .story-divider {{
                border: 0;
                height: 1px;
                background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0));
                margin: 50px 0;
            }}
            
            .article-footer {{
                margin-top: 30px;
                font-size: 0.8rem;
                text-align: center;
                color: #888;
                font-family: sans-serif;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>The Tempe Torch</h1>
            <div class="tagline">The Sunday Longform Edition • {datetime.now().strftime('%B %d, %Y')}</div>
        </header>
        {main_content}
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Published {OUTPUT_HTML_PATH}")

def main():
    print("NEWSROOM: LONGFORM EDITION")
    # GitHub Actions check
    if os.environ.get('CI') == 'true':
        sections = run_newsroom()
        publish_broadsheet(sections)
    else:
        while True:
            print(f"\n--- EDITOR START: {datetime.now().strftime('%H:%M')} ---")
            sections = run_newsroom()
            publish_broadsheet(sections)
            print("--- EDITOR SLEEPING ---")
            time.sleep(REFRESH_RATE_MINUTES * 60)

if __name__ == "__main__":
    main()
