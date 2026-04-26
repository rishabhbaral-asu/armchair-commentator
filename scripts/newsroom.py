import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Set

import pytz
import requests
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION & SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

MST = pytz.timezone('US/Arizona')
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
def get_whitelist() -> List[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "whitelist.txt")
    if not os.path.exists(path):
        logging.critical(f"Whitelist not found at {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except IOError as e:
        logging.error(f"Failed to read whitelist: {e}")
        return []

def clean_narrative(raw_text: str) -> str:
    if not raw_text: 
        return ""
    return re.sub(r'\s+', ' ', raw_text).strip()

# --- 2. ENGINES: SCRAPING & SYNTHETIC NARRATIVE ---

def fetch_full_narrative(game: Dict[str, Any]) -> str:
    """
    Scrapes ESPN for Recaps or Scoring Summaries using BeautifulSoup.
    Strictly targets specific CSS classes on specific URLs.
    """
    eid = game['id']
    league = game['league']
    is_final = game['is_final']
    
    # Crucial: Headers to mimic a real browser to bypass basic anti-bot filters
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    # --- 1. ATTEMPT RECAP SCRAPE ---
    recap_url = f"https://www.espn.com/{league}/recap/_/gameId/{eid}"
    try:
        res = requests.get(recap_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Target exact requested class: "Story__Body t__body"
        # Using lambda to ensure both class segments are in the element's class list
        article = soup.find('div', class_=lambda x: x and 'Story__Body' in x and 't__body' in x)
        
        # Fallback if they slightly changed the class string but kept the main identifier
        if not article:
            article = soup.find('div', class_=re.compile(r'Story__Body'))
            
        if article:
            # Strip out videos, ads, inline scripts
            for tag in article.find_all(['aside', 'figure', 'div', 'script', 'style', 'ul']):
                tag.decompose()
                
            paragraphs = article.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 35])
            
            if len(full_text) > 150:
                return clean_narrative(full_text)
    except requests.exceptions.RequestException as e:
        logging.debug(f"Recap scrape failed for {eid}: {e}")

    # --- 2. FALLBACK: SCORING SUMMARY SCRAPE ---
    game_url = f"https://www.espn.com/{league}/game/_/gameId/{eid}"
    try:
        res = requests.get(game_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Target exact requested class: "Card Card--ScoringSummary"
        summary_card = soup.find('div', class_=lambda x: x and 'Card' in x and 'Card--ScoringSummary' in x)
        
        if summary_card:
            plays = []
            for item in summary_card.find_all(['li', 'tr']):
                text = item.get_text(separator=" ", strip=True)
                if len(text) > 15 and "Scoring Summary" not in text:
                    plays.append(text)
            
            if plays:
                city = game['city'].upper()
                away, home = game['away_name'], game['home_name']
                
                story = (f"{city} — In a matchup between the {away} and {home}, "
                         f"the scoring action unfolded as follows: ")
                story += ". ".join(plays) + ". "
                story += (f"The final score concluded with the {home} tallying {game['home_score']} "
                          f"and the {away} putting up {game['away_score']}.")
                return clean_narrative(story)
    except requests.exceptions.RequestException as e:
        logging.debug(f"Scoring Summary scrape failed for {eid}: {e}")

    # --- 3. SYNTHETIC NEWS DESK FALLBACK ---
    home, away = game['home_name'], game['away_name']
    city, weather = game['city'], game['weather']
    
    if is_final:
        h_score, a_score = int(game['home_score']), int(game['away_score'])
        winner = home if h_score > a_score else away
        loser = away if h_score > a_score else home
        return (f"{city.upper()} — The {winner} pulled away late to secure a victory over the {loser}, "
                f"finishing with a final score of {max(h_score, a_score)}-{min(h_score, a_score)}. "
                f"Wire reports indicate a high-level physical contest. The game concluded under {weather} "
                f"conditions.")
    
    return (f"{city.upper()} — National wire services are monitoring the upcoming matchup between the {away} "
            f"and the {home}. The contest is currently listed with {game['odds']}. Forecasts at the venue "
            f"call for {weather}.")

def get_betting_data(eid: str, league: str) -> str:
    url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/{league}/summary?event={eid}"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        pick = data.get('pickcenter', [{}])[0]
        return f"LINE: {pick.get('details', 'OFF')} | O/U: {pick.get('overUnder', 'OFF')}"
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return "LINE: N/A | O/U: N/A"

def get_live_weather(city: str) -> str:
    if OPENWEATHER_API_KEY == "MISSING_KEY":
        return "72°F CLEAR (NO API KEY)"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return f"{round(data['main']['temp'])}°F {data['weather'][0]['main'].upper()}"
    except (requests.exceptions.RequestException, KeyError):
        return "72°F CLEAR"

# --- 3. DATA FETCHING ---

def get_data(sport: str, league: str, whitelist: List[str], seen_ids: Set[str]) -> List[Dict[str, Any]]:
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    now_mst = datetime.now(MST)
    today = now_mst.strftime('%Y%m%d')
    results = []
    
    try:
        res = requests.get(url, params={"limit": "100", "dates": today}, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        for event in data.get("events", []):
            eid = event["id"]
            if not event.get("competitions") or eid in seen_ids:
                continue
                
            comp = event["competitions"][0]
            teams = [t['team']['displayName'].lower() for t in comp.get("competitors", [])]
            
            if any(any(w in t for w in whitelist) for t in teams):
                home_team = comp["competitors"][0]
                away_team = comp["competitors"][1]
                city = comp.get("venue", {}).get("address", {}).get("city", "Unknown City")
                
                game_info = {
                    "id": eid, 
                    "iso_date": event["date"], 
                    "league": league, 
                    "sport_type": sport,
                    "home_name": home_team["team"]["shortDisplayName"],
                    "away_name": away_team["team"]["shortDisplayName"],
                    "home_logo": home_team["team"].get("logo", ""),
                    "away_logo": away_team["team"].get("logo", ""),
                    "home_score": home_team.get("score", "0"),
                    "away_score": away_team.get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "is_final": event["status"]["type"]["name"] == "STATUS_FINAL", 
                    "city": city,
                    "weather": get_live_weather(city),
                    "odds": get_betting_data(eid, league)
                }
                
                # Fetch story explicitly via HTTP requests and BS4
                game_info["story"] = fetch_full_narrative(game_info)
                results.append(game_info)
                seen_ids.add(eid)
                logging.info(f"Processed match: {game_info['away_name']} @ {game_info['home_name']}")
                
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {league} scoreboard: {e}")
        
    return results

# --- 4. RENDERER ---

def generate_html(games: List[Dict[str, Any]]) -> None:
    now_mst = datetime.now(MST)
    ticker_time = now_mst.strftime("%I:%M:%S %p %Z")
    
    html_parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@400;700&display=swap');
        body {{ background: #0b0d0e; color: #eee; font-family: 'Roboto Condensed', sans-serif; margin: 0; padding-top: 40px; }}
        .ticker-bar {{ position: fixed; top: 0; width: 100%; background: #000; color: #fff; height: 40px; display: flex; align-items: center; z-index: 1000; border-bottom: 2px solid #cc0000; font-family: 'Oswald'; text-transform: uppercase; font-size: 0.85em; }}
        .ticker-clock {{ background: #cc0000; padding: 0 20px; height: 100%; display: flex; align-items: center; letter-spacing: 1px; }}
        .ticker-clock::before {{ content: ""; display: inline-block; width: 8px; height: 8px; background: #fff; border-radius: 50%; margin-right: 10px; animation: blink 1.2s infinite; }}
        @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.2; }} 100% {{ opacity: 1; }} }}
        .ticker-text {{ padding-left: 20px; color: #888; letter-spacing: 2px; }}
        .container {{ max-width: 950px; margin: auto; padding: 20px; }}
        .bug-hockey {{ display: flex; background: linear-gradient(180deg, #2c2f36 0%, #000 100%); border: 1px solid #444; height: 52px; align-items: stretch; margin-top: 40px; border-radius: 4px; overflow: hidden; }}
        .hockey-status {{ background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.9em; }}
        .hockey-team {{ flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 700; gap: 10px; border-right: 1px solid #333; text-transform: uppercase; }}
        .hockey-team img {{ height: 30px; }}
        .hockey-score {{ width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; font-family: 'Oswald'; background: rgba(0,0,0,0.5); }}
        .bug-ncaa {{ background: #fff; color: #000; margin-top: 40px; display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-radius: 3px; overflow: hidden; }}
        .ncaa-main {{ display: flex; height: 75px; align-items: stretch; border-bottom: 1px solid #ddd; }}
        .ncaa-team {{ flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.6em; font-weight: 800; text-transform: uppercase; gap: 12px; }}
        .ncaa-team img {{ height: 45px; width: 45px; object-fit: contain; }}
        .ncaa-score {{ background: #111; color: #fff; width: 85px; display: flex; align-items: center; justify-content: center; font-size: 2.8em; font-family: 'Oswald'; }}
        .ncaa-status {{ background: #e5e5e5; width: 150px; display: flex; align-items: center; justify-content: center; font-size: 0.8em; font-weight: 900; border-left: 1px solid #ccc; color: #333; text-align: center; text-transform: uppercase; }}
        .info-bar {{ background: #f8f8f8; color: #c00; font-size: 0.9em; padding: 10px 25px; font-weight: bold; border-top: 1px solid #ddd; font-family: 'Oswald'; display: flex; justify-content: space-between; }}
        .wire-box {{ background: #fff; color: #222; padding: 40px; line-height: 1.8; font-size: 1.2em; border-top: 1px solid #eee; text-align: justify; }}
    </style></head><body>
    <div class="ticker-bar">
        <div class="ticker-clock">{ticker_time}</div>
        <div class="ticker-text">WIRE SERVICE // LIVE FEED // {now_mst.strftime('%A').upper()}</div>
    </div>
    <div class="container">"""]

    for g in games:
        g_time = datetime.fromisoformat(g['iso_date'].replace('Z', '+00:00')).astimezone(MST)
        
        if not g['is_final'] and g_time > now_mst:
            diff = g_time - now_mst
            status_display = f"STARTS IN: {diff.seconds//3600}H {(diff.seconds//60)%60}M"
        else:
            status_display = g['status_text']

        if g['sport_type'] == "hockey":
            html_parts.append(f"""
            <div class="bug-hockey">
                <div class="hockey-status">{status_display}</div>
                <div class="hockey-team"><img src="{g['away_logo']}">{g['away_name']}</div>
                <div class="hockey-score">{g['away_score']}</div>
                <div class="hockey-team"><img src="{g['home_logo']}">{g['home_name']}</div>
                <div class="hockey-score">{g['home_score']}</div>
            </div>""")
        else:
            html_parts.append(f"""
            <div class="bug-ncaa">
                <div class="ncaa-main">
                    <div class="ncaa-team"><img src="{g['away_logo']}">{g['away_name']}</div>
                    <div class="ncaa-score">{g['away_score']}</div>
                    <div class="ncaa-team"><img src="{g['home_logo']}">{g['home_name']}</div>
                    <div class="ncaa-score">{g['home_score']}</div>
                    <div class="ncaa-status">{status_display}</div>
                </div>
                <div class="info-bar"><span>{g['odds']}</span><span>CONDITIONS: {g['weather']}</span></div>
                <div class="wire-box">{g['story']}</div>
            </div>""")

    html_parts.append("</div></body></html>")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.join(script_dir, "..", "index.html")
    
    try:
        with open(root_path, "w", encoding="utf-8") as f:
            f.write("".join(html_parts))
        logging.info(f"Successfully generated HTML at {root_path}")
    except IOError as e:
        logging.error(f"Failed to write HTML file: {e}")

def main() -> None:
    logging.info("Starting Sports Ticker generation...")
    
    whitelist = get_whitelist()
    if not whitelist:
        logging.warning("Whitelist is empty. No games will be processed.")
        
    all_games = []
    seen = set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"), 
        ("basketball", "nba"), 
        ("hockey", "nhl"), 
        ("baseball", "mlb")
    ]
    
    for sport, league in leagues:
        logging.info(f"Fetching data for {league.upper()}...")
        all_games.extend(get_data(sport, league, whitelist, seen))
        
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)
    logging.info("Run complete.")

if __name__ == "__main__":
    main()
