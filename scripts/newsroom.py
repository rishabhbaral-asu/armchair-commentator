import json
import time
import os
import requests
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
WHITELIST_PATH = Path("scripts/whitelist.json")
REFRESH_RATE_MINUTES = 5
WINDOW_DAYS_BACK = 30
WINDOW_DAYS_FWD = 14

def load_whitelist():
    """Loads your manual list of teams."""
    if not WHITELIST_PATH.exists():
        print("⚠️ No whitelist.json found! Creating empty one.")
        with open(WHITELIST_PATH, "w") as f: json.dump([], f)
        return []
    with open(WHITELIST_PATH, "r") as f:
        # Load and clean list
        return [t.strip() for t in json.load(f)]

def is_approved_game(event, whitelist):
    """
    Checks if a team is in the whitelist using WHOLE WORD matching only.
    This prevents 'India' from matching 'Indiana'.
    """
    try:
        c = event['competitions'][0]
        teams = [
            c['competitors'][0]['team']['displayName'], 
            c['competitors'][1]['team']['displayName']
        ]
    except: return False

    for team in teams:
        # Normalize the team name from the API
        t_clean = team.strip()
        
        for target in whitelist:
            # Create a regex pattern that looks for the target word as a WHOLE word.
            # \b matches the boundary between a word character and a non-word character.
            # flags=re.IGNORECASE makes it case-insensitive.
            pattern = rf"\b{re.escape(target)}\b"
            
            if re.search(pattern, t_clean, flags=re.IGNORECASE): 
                return True
    return False

# --- STORYTELLER ENGINE ---

class Storyteller:
    def __init__(self, game):
