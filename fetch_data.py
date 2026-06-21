import os, re, json, requests
from datetime import datetime, timedelta
from github import Github

# ============================================================
# CREDENTIALS
# ============================================================
FOOTBALL_API_KEY = os.environ['FOOTBALL_API_KEY']
GITHUB_TOKEN     = os.environ['GITHUB_TOKEN']
REPO_NAME        = "NeerajGH2026/fifa-wc2026-predictions"

# ============================================================
# DATES
# ============================================================
today     = datetime.utcnow().date()
yesterday = today - timedelta(days=1)

headers = {"X-Auth-Token": FOOTBALL_API_KEY}
BASE    = "https://api.football-data.org/v4"

# ============================================================
# WC 2026 COMPETITION CODE
# ============================================================
WC_ID = "CL"  # We'll detect the right one below

def get_wc_competition_id():
    r = requests.get(f"{BASE}/competitions", headers=headers)
    comps = r.json().get("competitions", [])
    for c in comps:
        if "World Cup" in c.get("name","") and "2026" in str(c.get("name","") + str(c.get("id",""))):
            return c["id"]
    # fallback — search all matches for WC teams
    return "WC"

# ============================================================
# FETCH YESTERDAY'S RESULTS
# ============================================================
print(f"📅 Fetching results for {yesterday}...")
r = requests.get(
    f"{BASE}/matches",
    headers=headers,
    params={"dateFrom": str(yesterday), "dateTo": str(yesterday)}
)
all_matches = r.json().get("matches", [])

# Filter for World Cup matches only
wc_teams = [
    "Argentina","Australia","Belgium","Brazil","Cameroon","Canada",
    "Chile","Colombia","Costa Rica","Croatia","Denmark","Ecuador",
    "Egypt","England","France","Germany","Ghana","Honduras","Iran",
    "Italy","Japan","Mexico","Morocco","Netherlands","New Zealand",
    "Nigeria","Panama","Paraguay","Peru","Poland","Portugal",
    "Saudi Arabia","Senegal","Serbia","South Korea","Spain","Sweden",
    "Switzerland","Tunisia","Ukraine","United States","Uruguay",
    "Venezuela","Cabo Verde","Curaçao","Ivory Coast","Uzbekistan",
    "Kuwait","Indonesia","Thailand"
]

yesterdays_results = []
for m in all_matches:
    home = m["homeTeam"]["name"]
    away = m["awayTeam"]["name"]
    status = m["status"]
    if status == "FINISHED":
        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]
        # Include if either team looks like a WC team
        if any(t in home or home in t for t in wc_teams) or \
           any(t in away or away in t for t in wc_teams):
            yesterdays_results.append({
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score
            })
            print(f"  ✅ {home} {home_score}-{away_score} {away}")

print(f"Found {len(yesterdays_results)} WC results for yesterday")

# ============================================================
# FETCH TODAY'S FIXTURES
# ============================================================
print(f"\n📅 Fetching fixtures for {today}...")
r2 = requests.get(
    f"{BASE}/matches",
    headers=headers,
    params={"dateFrom": str(today), "dateTo": str(today)}
)
todays_all = r2.json().get("matches", [])

todays_matches = []
for m in todays_all:
    home = m["homeTeam"]["name"]
    away = m["awayTeam"]["name"]
    if any(t in home or home in t for t in wc_teams) or \
       any(t in away or away in t for t in wc_teams):
        todays_matches.append((home, away))
        print(f"  ⚽ {home} vs {away}")

print(f"Found {len(todays_matches)} WC fixtures for today")

# ============================================================
# UPDATE predict.py ON GITHUB
# ============================================================
print("\n📝 Updating predict.py on GitHub...")

g    = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
file = repo.get_contents("predict.py")
content = file.decoded_content.decode("utf-8")

# Build new yesterdays_results block
results_lines = "yesterdays_results = [\n"
for r in yesterdays_results:
    results_lines += f"    {{'home':'{r['home']}','away':'{r['away']}','home_score':{r['home_score']},'away_score':{r['away_score']}}},\n"
results_lines += "]"

# Build new todays_matches block
matches_lines = "todays_matches = [\n"
for home, away in todays_matches:
    matches_lines += f"    ('{home}', '{away}'),\n"
matches_lines += "]"

# Replace in file using regex
content = re.sub(
    r"yesterdays_results = \[.*?\]",
    results_lines,
    content,
    flags=re.DOTALL
)
content = re.sub(
    r"todays_matches = \[.*?\]",
    matches_lines,
    content,
    flags=re.DOTALL
)

# Commit back to GitHub
repo.update_file(
    "predict.py",
    f"🤖 Auto-update: results {yesterday} + fixtures {today}",
    content,
    file.sha
)

print("✅ predict.py updated successfully!")
print(f"  Yesterday: {len(yesterdays_results)} results")
print(f"  Today: {len(todays_matches)} fixtures")
