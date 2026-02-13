# ... imports ...
import re  # <--- MAKE SURE THIS IS IMPORTED AT THE TOP

# ... existing code ...

def is_approved_game(event, whitelist):
    """
    Checks if a team is in the whitelist using WORD BOUNDARIES.
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
        t_clean = team.lower().strip()
        for target in whitelist:
            # \b matches the start/end of a word. 
            # So \bIndia\b matches "India" but NOT "Indiana"
            pattern = rf"\b{re.escape(target)}\b"
            
            if re.search(pattern, t_clean): 
                return True
    return False

# ... rest of script ...
