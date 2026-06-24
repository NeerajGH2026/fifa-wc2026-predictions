import requests
import os
from datetime import datetime, timedelta, timezone

# ─── API CONFIG ───────────────────────────────────────────────
API_KEY  = os.environ.get("FOOTBALL_API_KEY", "")
HEADERS  = {"X-Auth-Token": API_KEY}
BASE_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# ─── DATE SETUP ───────────────────────────────────────────────
# Actions runs at 10:30 UTC = 5:30 AM CDT
# CDT = UTC-5. We define "today" and "yesterday" in CDT terms,
# then query a wide enough UTC window to catch all CDT-day matches.
#
# A full CDT calendar day spans:
#   05:00 UTC (midnight CDT) → 05:00 UTC next day
# So to get ALL of CDT-today's matches we query:
#   dateFrom = yesterday_utc (catches midnight-5AM UTC = prev CDT evening)
#   dateTo   = tomorrow_utc  (catches 11PM CDT = early next UTC day)
# Then we FILTER by CDT date to keep only the right day's matches.

CDT = timezone(timedelta(hours=-5))
now_utc       = datetime.now(timezone.utc)
now_cdt       = now_utc.astimezone(CDT)
today_cdt     = now_cdt.date()
yesterday_cdt = today_cdt - timedelta(days=1)

# UTC window for API queries
today_utc     = now_utc.date()
yesterday_utc = today_utc - timedelta(days=1)
two_days_ago  = today_utc - timedelta(days=2)
tomorrow_utc  = today_utc + timedelta(days=1)

print(f"🕐 Script running at: {now_utc.strftime('%Y-%m-%d %H:%M UTC')} / {now_cdt.strftime('%Y-%m-%d %H:%M CDT')}")
print(f"📅 CDT today={today_cdt}  CDT yesterday={yesterday_cdt}")

# ─── FETCH FINISHED RESULTS ───────────────────────────────────
# Look back 2 UTC days to catch late CDT matches stored under next UTC date
results_params = {
    "dateFrom": str(two_days_ago),
    "dateTo":   str(today_utc),    # include today UTC — catches late CDT last night
    "status":   "FINISHED"
}
print(f"\n📡 Fetching results: {two_days_ago} → {today_utc} (status=FINISHED)...")
results_resp   = requests.get(BASE_URL, headers=HEADERS, params=results_params)
all_finished   = results_resp.json().get("matches", [])
print(f"   Found {len(all_finished)} finished matches in window")

# Filter: keep only matches whose CDT date == yesterday_cdt
yesterdays_results_raw = []
for m in all_finished:
    utc_date_str = m.get("utcDate", "")
    if not utc_date_str:
        continue
    match_dt_utc = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
    match_dt_cdt = match_dt_utc.astimezone(CDT)
    if match_dt_cdt.date() == yesterday_cdt:
        hg = m["score"]["fullTime"]["home"]
        ag = m["score"]["fullTime"]["away"]
        if hg is None or ag is None:
            continue
        yesterdays_results_raw.append({
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"],
            "home_score": hg,
            "away_score": ag,
            "match_dt_cdt": str(match_dt_cdt)
        })

print(f"   After CDT filter (yesterday={yesterday_cdt}): {len(yesterdays_results_raw)} matches")

# ─── FETCH TODAY'S FIXTURES ───────────────────────────────────
# Query yesterday→tomorrow UTC to catch full CDT day
fixtures_params = {
    "dateFrom": str(yesterday_utc),
    "dateTo":   str(tomorrow_utc),
}
print(f"\n📡 Fetching fixtures: {yesterday_utc} → {tomorrow_utc}...")
fixtures_resp  = requests.get(BASE_URL, headers=HEADERS, params=fixtures_params)
all_matches    = fixtures_resp.json().get("matches", [])
print(f"   Found {len(all_matches)} total matches in window")

# Filter: keep only matches whose CDT date == today_cdt AND not yet finished
todays_fixtures_raw = []
for m in all_matches:
    utc_date_str = m.get("utcDate", "")
    if not utc_date_str:
        continue
    match_dt_utc = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
    match_dt_cdt = match_dt_utc.astimezone(CDT)
    match_status = m.get("status", "")
    # CDT date must be today, and match must not be finished
    if match_dt_cdt.date() == today_cdt and match_status not in ("FINISHED", "AWARDED"):
        todays_fixtures_raw.append({
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"],
            "time": utc_date_str,
            "time_cdt": match_dt_cdt.strftime("%I:%M %p CDT"),
            "status": match_status
        })

print(f"   After CDT filter (today={today_cdt}): {len(todays_fixtures_raw)} fixtures")

# ─── PRINT SUMMARY ────────────────────────────────────────────
print(f"\n✅ Yesterday's results ({len(yesterdays_results_raw)}):")
for r in yesterdays_results_raw:
    winner = r['home'] if r['home_score'] > r['away_score'] else \
             r['away'] if r['away_score'] > r['home_score'] else 'Draw'
    print(f"   {r['home']} {r['home_score']}-{r['away_score']} {r['away']} → {winner}  [{r['match_dt_cdt']}]")

print(f"\n⚽ Today's fixtures ({len(todays_fixtures_raw)}):")
for f in todays_fixtures_raw:
    print(f"   {f['home']} vs {f['away']}  {f['time_cdt']}  [{f['status']}]")

if not todays_fixtures_raw:
    print("⚠️  WARNING: No fixtures found for today.")

# ─── BUILD predict.py ENTRIES ─────────────────────────────────
results_entries = []
for r in yesterdays_results_raw:
    results_entries.append(
        f"    {{'home':'{r['home']}','away':'{r['away']}','home_score':{r['home_score']},'away_score':{r['away_score']}}},"
    )

fixtures_entries = []
for f in todays_fixtures_raw:
    results_entries_line = f"    {{'home':'{f['home']}','away':'{f['away']}','time':'{f['time']}','time_cdt':'{f['time_cdt']}'}},"
    fixtures_entries.append(results_entries_line)

# ─── WRITE predict.py ─────────────────────────────────────────
results_block  = "\n".join(results_entries)
fixtures_block = "\n".join(fixtures_entries)

predict_py = f"""# Auto-generated by fetch_data.py on {now_utc.strftime("%Y-%m-%d %H:%M UTC")}
# CDT date: today={today_cdt}  yesterday={yesterday_cdt}

yesterdays_results = [
{results_block}
]

todays_matches = [
{fixtures_block}
]
"""

with open("predict.py", "w") as f:
    f.write(predict_py)

print(f"\n✅ predict.py written: {len(results_entries)} results | {len(fixtures_entries)} fixtures")
