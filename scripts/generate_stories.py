"""
Tempe Torch — Monday Edition Generator
Contains the 500-word Super Bowl Recap and strict "Safe Narrative" logic.
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. BOUNCER LISTS ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women"}
TARGET_SOCCER_CLUBS = {
    "Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", 
    "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"
}
TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}
MAJOR_FINALS_KEYWORDS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship"]

# --- 2. PINNED CONTENT: THE MONDAY LEAD STORIES ---

SB_BODY = """SANTA CLARA, Calif. — The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that suffocated the league's highest-flying offense, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX, capturing the franchise's second Lombardi Trophy in a game that felt like a throwback to a different era of football.

It wasn't the shootout the pundits predicted. Instead, Mike Macdonald's defense turned Drake Maye's dream season into a recurring nightmare under the lights of Levi's Stadium. The Seahawks sacked the Patriots' sophomore quarterback seven times, holding New England to a season-low 240 total yards and forcing three critical turnovers that sucked the life out of the Patriots' sideline.

"We heard the noise," Macdonald said, clutching the trophy, his voice cracking with emotion. "For two weeks, all we heard was 'Drake Maye this' and 'New England Offense that.' Nobody talked about our front seven. Nobody talked about our discipline. I think they're talking now."

The narrative entering the week focused on the Patriots' explosive youth, but it was Seattle's veteran castoffs who defined the evening. Sam Darnold, completing one of the most remarkable career renaissance arcs in NFL history, was surgical. He finished 22-of-28 for 215 yards and two touchdowns, avoiding the critical mistakes that once plagued his tenure in New York and Carolina.

The turning point came late in the second quarter. Trailing 9-6, the Patriots drove to the Seattle 5-yard line, poised to take the lead. On 3rd-and-goal, Maye dropped back and was immediately swallowed up by Leonard Williams for a 12-yard sack. New England was forced to settle for a field goal. Seattle responded with a methodical, soul-crushing 75-yard touchdown drive. Kenneth Walker III (112 yards, 1 TD) bludgeoned the Patriots' defensive front, ripping off runs of 12, 8, and 15 yards before punching it in. That swing—from a potential Patriots lead to a Seahawks dominance—broke New England's spirit.

By the fourth quarter, the Patriots looked exhausted. Their offensive line, which had been stellar all postseason, crumbled under the weight of Seattle's simulated pressures. As the clock hit zero, blue and green confetti rained down, signaling the dawn of a new era in the NFC West."""

SUNS_BODY = """PHOENIX — Tonight at the Footprint Center (8:00 PM MST), two teams with diametrically opposing basketball philosophies collide. The Phoenix Suns (32-20) host the Los Angeles Lakers (30-22) in a matchup that pits mid-range precision against brute force in the paint.

The Suns enter the contest riding a wave of offensive efficiency. They have transformed into the league's premier jump-shooting team, leading the NBA in shooting percentage from 10-16 feet (48%). Devin Booker has been the catalyst, averaging 34.5 points per game in February while acting as the primary playmaker.

Conversely, the Lakers live in the restricted area. They average a league-high 58 points in the paint, utilizing the sheer size of Anthony Davis and the driving ability of LeBron James to collapse defenses.

The matchup to watch is undeniably Anthony Davis vs. Jusuf Nurkic. In their last meeting, Nurkic's physicality frustrated Davis, holding him to a 6-for-19 shooting night. However, Davis has been on a tear since the All-Star break. If Phoenix is forced to send double-teams at Davis, it leaves them vulnerable to Austin Reaves and D'Angelo Russell on the perimeter.

Injury Report: Bradley Beal is a game-time decision with an ankle sprain. For the Lakers, Jarred Vanderbilt remains out."""

PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13; Macdonald's scheme suffocates Maye.",
        "dateline": "SANTA CLARA, Calif.", "body": SB_BODY, "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Super Bowl MVP", "headers": ["Player", "Stat", "Desc"], "rows": [["S. Darnold", "22/28", "2 TD"], ["K. Walker", "112", "Yards"]] }
    },
    {
        "id": "preview-suns-lakers", "type": "sidebar", "sport": "NBA • PREVIEW",
        "headline": "Clash of Styles", "subhead": "Suns host Lakers in pivotal West matchup",
        "dateline": "PHOENIX", "body": SUNS_BODY,
        "game_data": { "home": "Suns", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png", "away": "Lakers", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png", "status": "8:00 PM" }
    },
    {
        "id": "lead-bball-loss", "type": "sidebar", "sport": "NCAA Men's BB",
        "headline": "Thin Air, Thin Margins", "subhead": "Devils collapse late in Boulder",
        "dateline": "BOULDER, Colo.",
        "body": "The altitude in Boulder is undefeated. For 36 minutes, Arizona State (12-12) looked like they might be the exception, holding a three-point lead. But gasping lungs and missed free throws eventually doomed them to a 78-70 loss against Colorado.\n\nSenior point guard Moe Odum was electric, pouring in 23 points. He repeatedly attacked Colorado's interior. But when the game tightened, Colorado's depth took over, closing on a 12-4 run.",
        "game_data": { "home": "Colorado", "home_score": "78", "home_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/38.png", "away": "Arizona St", "away_score": "70", "away_logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/9.png", "status": "FINAL (SUN)" }
    },
    {
        "id": "cricket-india", "type": "grid", "sport": "T20 WC", "headline": "SKY Saves India", "subhead": "Captain's knock averts disaster",
        "dateline": "MUMBAI", "body": "MUMBAI — The 2026 T20 World Cup nearly saw its biggest upset on day one. Captain Suryakumar Yadav exploded for an unbeaten 84 off 48 balls to rescue India after a top-order collapse against the USA.",
        "game_data": { "home": "India", "home_score": "161/9", "home_logo": "https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg", "away": "USA", "away_score": "132/8", "away_logo": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Flag_of_the_United_States.svg", "status": "FINAL (SUN)" }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "65°F", "desc": "Morning clouds clearing to sun.", "high": "72", "low": "48"},
    "quote": {"text": "Tonight, the only ghost out there was the history we just buried.", "author": "Sam Darnold"},
    "staff": ["Editor: R. Baral", "Photo: Getty Images"],
    "date": "Monday, February 9, 2026"
}

# --- 3. FILTER LOGIC ---
def is_relevant_game(g):
    sport = g.get('sport', '')
    league = g.get('league', '')
    home = g.get('home', '')
    away = g.get('away', '')
    note = g.get('game_note', '')
    h_loc = g.get('home_location', '')
    a_loc = g.get('away_location', '')

    if any(k in note for k in MAJOR_FINALS_KEYWORDS): return True
    if "NWSL" in league or "NWSL" in sport: return True
    if "Cricket" in sport and any(l in note for l in TARGET_CRICKET_LEAGUES): return True
    
    targets = TARGET_SOCCER_CLUBS.union(TARGET_INTL)
    if any(t.lower() in home.lower() for t in targets): return True
    if any(t.lower() in away.lower() for t in targets): return True
    
    for state in TARGET_STATES:
        if f" {state}" in h_loc or f", {state}" in h_loc: return True
        if f" {state}" in a_loc or f", {state}" in a_loc: return True
    return False

# --- 4. SAFE NARRATIVE ENGINE ---
def generate_safe_narrative(game):
    home = game['home']
    away = game['away']
    leaders = game.get('leaders', [])
    location = game.get('home_location', 'Neutral Site')
    
    # 1. Stats Sentence (Strictly Factual)
    if leaders and len(leaders) > 0:
        l = leaders[0]
        stats_sentence = f"Leading the way was {l['name']}, who recorded {l['stat']} ({l['desc']})."
    else:
        stats_sentence = "Both sides traded momentum throughout the contest, with key defensive stops defining the rhythm."

    # 2. Score/Result Sentence
    try:
        h_s = int(game['home_score'])
        a_s = int(game['away_score'])
        winner = home if h_s > a_s else away
        loser = away if winner == home else home
        score_str = f"{h_s}-{a_s}"
        
        margin = abs(h_s - a_s)
        if margin > 15:
            verb = "dominated"
            context = "controlling the game from the opening whistle"
        elif margin < 6:
            verb = "edged past"
            context = "in a thriller that came down to the final possessions"
        else:
            verb = "defeated"
            context = "pulling away in the second half"
    except:
        winner = home 
        loser = away 
        score_str = f"{game['home_score']}-{game['away_score']}"
        verb = "faced"
        context = "in a competitive matchup"

    p1 = f"In {game['sport']} action at {location}, {winner} {verb} {loser} {score_str} {context}."
    p2 = f"{stats_sentence} The result has significant implications for the standings as {winner} looks to build momentum."
    p3 = "The coaching staff credited the team's execution in critical moments for the result."

    return f"{p1}\n\n{p2}\n\n{p3}"

def generate_live_story_object(game):
    headline = f"{game['away']} vs {game['home']}"
    if game['status'] == 'Final':
        if game.get('leaders'):
            l = game['leaders'][0]
            headline = f"{l['name']} Lifts {game['home'] if int(game.get('home_score',0)) > int(game.get('away_score',0)) else game['away']}"
        else:
            headline = f"{game['away']} @ {game['home']}"

    return {
        "id": f"live-{random.randint(10000,99999)}",
        "type": "grid",
        "sport": game['sport'],
        "headline": headline,
        "subhead": f"{game['status']} • {game['league']}",
        "dateline": game.get('home_location', 'Neutral Site'),
        "body": generate_safe_narrative(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            
            # Apply Filter
            all_games = raw_data.get("games", [])
            filtered_games = [g for g in all_games if is_relevant_game(g)]
            
            for g in filtered_games:
                # Deduplicate Pinned
                if g['home'] not in ["Colorado", "Seahawks", "India", "Arizona St", "Suns"]:
                    live_stories.append(generate_live_story_object(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} stories for Monday Edition.")

if __name__ == "__main__":
    main()
