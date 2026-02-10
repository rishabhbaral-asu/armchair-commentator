import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- PINNED CONTENT (Classics) ---
PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13 to claim title",
        "dateline": "SANTA CLARA, Calif.", 
        "body": "The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that stifled one of the league's most potent offenses, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks and forcing three turnovers.\n\nSam Darnold was efficient, throwing for 215 yards and two touchdowns, finding a rhythm early that the Patriots could not match. Kenneth Walker III added 112 yards on the ground, controlling the clock and the tempo.",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Super Bowl MVP", "headers": ["Player", "Stat", "Desc"], "rows": [["S. Darnold", "22/28", "2 TD"], ["K. Walker", "112", "Yards"]] }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "65°F", "desc": "Clear skies.", "high": "72", "low": "48"},
    "quote": {"text": "Tonight, the only ghost out there was the history we just buried.", "author": "Sam Darnold"},
    "staff": ["Editor: R. Baral", "Data: ESPN API"],
    "date": datetime.now().strftime("%A, %B %d, %Y")
}

# --- VOCABULARY ENGINE ---
VERBS_WIN_BIG = ["crushed", "dismantled", "routed", "steamrolled", "dominated"]
VERBS_WIN_CLOSE = ["edged past", "outlasted", "survived", "squeaked by", "fended off"]

# Sport-specific terminology for that authentic feel
SPORT_CONTEXT = {
    "basketball": {"start": "Tip-off", "venue_action": "take the floor at", "unit": "points"},
    "football": {"start": "Kickoff", "venue_action": "clash at", "unit": "yards"},
    "soccer": {"start": "Kickoff", "venue_action": "meet at", "unit": "goals"},
    "baseball": {"start": "First pitch", "venue_action": "take the field at", "unit": "runs"},
    "hockey": {"start": "Puck drop", "venue_action": "face off at", "unit": "goals"},
    "cricket": {"start": "The match", "venue_action": "square off at", "unit": "runs"}
}

def get_sport_context(sport_name):
    for key, context in SPORT_CONTEXT.items():
        if key in sport_name.lower():
            return context
    return {"start": "Start time", "venue_action": "meet at", "unit": "points"}

def generate_headline(game, margin, state):
    # ESPN Style: Use the narrative hook if available
    if state == 'pre':
        if game.get('headline'): return game['headline']
        return f"{game['away']} at {game['home']}"
    
    if state == 'in':
        if abs(margin) > 10: return f"{game['home'] if margin > 0 else game['away']} in Command"
        return "Live: Tight Contest"
        
    # FINAL
    winner = game['home'] if margin > 0 else game['away']
    loser = game['away'] if margin > 0 else game['home']
    
    if abs(margin) >= 15: return f"{winner} Rout {loser}"
    elif abs(margin) <= 3: return f"{winner} Edges {loser}"
    else: return f"{winner} Defeat {loser}"

def generate_dynamic_narrative(game):
    home = game.get('home')
    away = game.get('away')
    venue = game.get('venue')
    dateline = game.get('dateline', venue)
    status = game.get('status', '')
    state = game.get('state', '')
    leaders = game.get('leaders', [])
    headline_note = game.get('headline', '')
    sport = game.get('sport', '')
    
    ctx = get_sport_context(sport)

    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        h_s, a_s, margin = 0, 0, 0

    # --- A. ESPN-STYLE PREVIEW ---
    if state == 'pre':
        # 1. The Narrative Hook (The "Why We Watch" sentence)
        if headline_note:
            hook = f"{headline_note}. That is the storyline dominating the conversation as"
        else:
            hook = "Two squads looking to establish momentum will collide when"

        # 2. The Setup (Venue & Stakes)
        lede = f"{dateline} — {hook} the {away} visit the {home}. The teams {ctx['venue_action']} {venue} with critical standings implications on the line."

        # 3. The Player Spotlight (The "Key Matchup")
        # ESPN previews always cite the star player's recent form.
        player_spotlight = ""
        if leaders:
            l = leaders[0]
            player_spotlight = (
                f"\n\nAll eyes will be on {home} star {l['name']}, who enters the contest "
                f"averaging {l['stat']} ({l['desc']}). The {away} defense will need to contain "
                f"the playmaker if they hope to secure a road victory."
            )
        else:
            player_spotlight = (
                f"\n\nBoth coaching staffs have emphasized execution in practice this week. "
                f"The matchup presents a clash of styles, with the {home} looking to push the tempo "
                f"against a disciplined {away} unit."
            )

        # 4. The Closer (Time & Broadcast feel)
        closer = f"\n\n{ctx['start']} is scheduled for {status}."

        return f"{lede}{player_spotlight}{closer}"

    # --- B. LIVE GAME (The Wire Update) ---
    if state == 'in':
        leader = home if margin > 0 else away
        trailer = away if margin > 0 else home
        
        if abs(margin) >= 15:
            return (
                f"{dateline} — It has been all {leader} so far at {venue}. They have opened up a commanding {h_s}-{a_s} lead over the {trailer}. "
                f"The offense has been clicking on all cylinders, while the defense has suffocated the {trailer} attack. "
                f"Current status: {status}."
            )
        elif abs(margin) <= 5:
            return (
                f"{dateline} — We have a thriller developing in {venue}. The {home} and {away} are trading scores in a tight contest, separated by just {abs(margin)} {ctx['unit']}. "
                f"The score sits at {h_s}-{a_s} as they battle through the {status}. "
                f"Every possession feels critical in what has become a defensive standoff."
            )
        else:
            return (
                f"{dateline} — Action is underway at {venue}. The {leader} currently hold the advantage with a {h_s}-{a_s} lead. "
                f"There is still plenty of time left in the {status} for a turnaround, but {leader} are controlling the flow of the game."
            )

    # --- C. FINAL RECAP (The AP Style Report) ---
    if state == 'post':
        winner = home if h_s > a_s else away
        loser = away if winner == home else home
        verb = random.choice(VERBS_WIN_BIG if abs(margin) > 15 else VERBS_WIN_CLOSE)
        
        stat_txt = "The team relied on a balanced attack to secure the victory."
        if leaders:
            l = leaders[0]
            stat_txt = f"They were sparked by a standout performance from {l['name']}, who finished with {l['stat']} ({l['desc']})."

        narrative = (
            f"{dateline} — The {winner} {verb} the {loser} {h_s}-{a_s} on {datetime.now().strftime('%A')}. "
            f"In front of the crowd at {venue}, {winner} executed their game plan to perfection. {stat_txt} "
        )
        
        if headline_note:
            narrative += f"\n\nThe win punctuates a week defined by the headline: {headline_note}."
            
        return narrative

    return "Updates to follow."

def generate_grid_item(game):
    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        margin = 0

    return {
        "id": f"game-{game.get('game_id')}",
        "type": "grid",
        "sport": game['sport'],
        "headline": generate_headline(game, margin, game['state']),
        "subhead": game['status'],
        "dateline": game['dateline'],
        "body": generate_dynamic_narrative(game),
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            for g in raw_data.get("games", []):
                # Dedupe Seahawks since they are in the lead story
                if g['home'] != "Seahawks" and g['away'] != "Seahawks":
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} Press-Ready Stories.")

if __name__ == "__main__":
    main()
