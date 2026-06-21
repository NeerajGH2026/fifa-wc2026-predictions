import os, re, requests
from datetime import datetime, timedelta
from github import Github

# ============================================================
# CREDENTIALS
# ============================================================
FOOTBALL_API_KEY = os.environ['FOOTBALL_API_KEY']
GITHUB_TOKEN     = os.environ['PAT_TOKEN']
REPO_NAME        = "NeerajGH2026/fifa-wc2026-predictions"

# ============================================================
# DATES
# ============================================================
today     = datetime.utcnow().date()
yesterday = today - timedelta(days=1)

headers = {"X-Auth-Token": FOOTBALL_API_KEY}
BASE    = "https://api.football-data.org/v4"

# ============================================================
# FETCH YESTERDAY'S WC RESULTS
# ============================================================
print(f"📅 Fetching WC results for {yesterday}...")
r = requests.get(
    f"{BASE}/competitions/WC/matches",
    headers=headers,
    params={"dateFrom": str(yesterday), "dateTo": str(yesterday), "status": "FINISHED"}
)
data = r.json()
print(f"API response status: {r.status_code}")

yesterdays_results = []
for m in data.get("matches", []):
    home       = m["homeTeam"]["name"]
    away       = m["awayTeam"]["name"]
    home_score = m["score"]["fullTime"]["home"]
    away_score = m["score"]["fullTime"]["away"]
    if home_score is not None and away_score is not None:
        yesterdays_results.append({
            "home": home,
            "away": away,
            "home_score": int(home_score),
            "away_score": int(away_score)
        })
        print(f"  ✅ {home} {home_score}-{away_score} {away}")

print(f"Found {len(yesterdays_results)} results for yesterday")

# ============================================================
# FETCH TODAY'S WC FIXTURES
# ============================================================
print(f"\n📅 Fetching WC fixtures for {today}...")
r2 = requests.get(
    f"{BASE}/competitions/WC/matches",
    headers=headers,
    params={"dateFrom": str(today), "dateTo": str(today), "status": "SCHEDULED"}
)
data2 = r2.json()
print(f"API response status: {r2.status_code}")

todays_matches = []
for m in data2.get("matches", []):
    home = m["homeTeam"]["name"]
    away = m["awayTeam"]["name"]
    todays_matches.append((home, away))
    print(f"  ⚽ {home} vs {away}")

print(f"Found {len(todays_matches)} fixtures for today")

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
