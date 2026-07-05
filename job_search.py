"""
Daily Robotics/ROS Job Search Bot
----------------------------------
Searches for robotics/ROS-related jobs using the Jooble API (free tier),
merges results into a persistent job store (docs/jobs.json) so nothing
is emailed twice, and sends a digest of only the NEW listings each day.

Runs automatically every day via GitHub Actions (see .github/workflows/daily-job-search.yml).
"""

import os
import json
import hashlib
import smtplib
import requests
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------------------------------------------------------
# CONFIG — edit these to tune your search
# ---------------------------------------------------------------------------

SEARCH_KEYWORDS = [
    "ROS2 robotics engineer",
    "robotics intern",
    "embedded systems robotics",
    "autonomous navigation engineer",
    "computer vision robotics",
]

LOCATION = "Bangalore, India"

# Jooble's "salary" field being non-empty is used as a rough "paid job" signal.
# Set to False if you want to see unpaid/unspecified listings too.
ONLY_SHOW_JOBS_WITH_SALARY_LISTED = False

MAX_RESULTS_PER_KEYWORD = 10

JOBS_JSON_PATH = "docs/jobs.json"

# ---------------------------------------------------------------------------
# SECRETS — pulled from GitHub Actions repo secrets, never hardcode these
# ---------------------------------------------------------------------------

JOOBLE_API_KEY = os.environ["JOOBLE_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

JOOBLE_URL = f"https://jooble.org/api/{JOOBLE_API_KEY}"

# GitHub Actions sets this automatically as "owner/repo" — no secret needed.
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
if "/" in GITHUB_REPOSITORY:
    _owner, _repo = GITHUB_REPOSITORY.split("/", 1)
    DASHBOARD_URL = f"https://{_owner}.github.io/{_repo}/"
else:
    DASHBOARD_URL = ""  # running locally, no dashboard link available


def job_id(link: str) -> str:
    """Stable id derived from the job link, so the same posting always maps to the same id."""
    return hashlib.md5(link.encode("utf-8")).hexdigest()[:12]


def search_jobs(keyword: str) -> list[dict]:
    """Query Jooble for a single keyword and return raw job dicts."""
    payload = {"keywords": keyword, "location": LOCATION}
    try:
        resp = requests.post(JOOBLE_URL, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json().get("jobs", [])[:MAX_RESULTS_PER_KEYWORD]
    except requests.RequestException as e:
        print(f"[warn] search failed for '{keyword}': {e}")
        return []


def collect_all_jobs() -> list[dict]:
    """Search every keyword, dedupe by job link (within this run), optionally filter by salary."""
    seen_links = set()
    all_jobs = []

    for keyword in SEARCH_KEYWORDS:
        for job in search_jobs(keyword):
            link = job.get("link")
            if not link or link in seen_links:
                continue
            if ONLY_SHOW_JOBS_WITH_SALARY_LISTED and not job.get("salary"):
                continue
            seen_links.add(link)
            all_jobs.append(job)

    return all_jobs


def load_existing_store(path: str = JOBS_JSON_PATH) -> dict:
    """Load the persistent job store, keyed by job id. Returns {} if it doesn't exist yet."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return {job["id"]: job for job in data.get("jobs", [])}
    except (json.JSONDecodeError, KeyError):
        return {}


def merge_and_find_new(raw_jobs: list[dict], existing_store: dict) -> tuple[dict, list[dict]]:
    """
    Merge freshly-scraped jobs into the existing store.
    Returns (updated_store, list_of_genuinely_new_job_records).
    Existing jobs (and their "applied" flag) are left untouched.
    """
    updated_store = dict(existing_store)
    new_records = []
    today = datetime.now(timezone.utc).isoformat()

    for job in raw_jobs:
        link = job.get("link", "")
        if not link:
            continue
        jid = job_id(link)
        if jid in updated_store:
            continue  # already seen on a previous day — skip, don't re-email or duplicate

        record = {
            "id": jid,
            "title": job.get("title", "Untitled role"),
            "company": job.get("company", "Unknown company"),
            "location": job.get("location", ""),
            "stipend": job.get("salary") or "Not listed",
            "jd": job.get("snippet", ""),
            "link": link,
            "source": "Indeed/Jooble",
            "first_seen": today,
            "applied": False,
        }
        updated_store[jid] = record
        new_records.append(record)

    return updated_store, new_records


def write_jobs_json(store: dict, path: str = JOBS_JSON_PATH):
    """Persist the full accumulated job store, newest first."""
    all_jobs = sorted(store.values(), key=lambda j: j.get("first_seen", ""), reverse=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "jobs": all_jobs,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(all_jobs)} total jobs (store) to {path}")


def build_email_html(new_jobs: list[dict]) -> str:
    dashboard_link_html = ""
    if DASHBOARD_URL:
        dashboard_link_html = f"""
        <div style="text-align:center;margin:16px 0 24px;">
            <a href="{DASHBOARD_URL}" style="background:#1a73e8;color:#fff;text-decoration:none;
               padding:10px 22px;border-radius:6px;font-weight:bold;font-size:14px;display:inline-block;">
                Open Dashboard →
            </a>
        </div>
        """

    if not new_jobs:
        return f"""
        <html><body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">
            <h2>🤖 No new listings today</h2>
            <p>Nothing new since yesterday's scan. Check the dashboard for everything found so far.</p>
            {dashboard_link_html}
        </body></html>
        """

    rows = []
    for job in new_jobs:
        rows.append(f"""
        <div style="margin-bottom:18px;padding:14px;border:1px solid #ddd;border-radius:8px;">
            <a href="{job['link']}" style="font-size:16px;font-weight:bold;text-decoration:none;color:#1a73e8;">{job['title']}</a>
            <div style="color:#555;font-size:14px;margin-top:4px;">{job['company']} &middot; {job['location']}</div>
            <div style="color:#555;font-size:13px;margin-top:2px;">💰 {job['stipend']}</div>
            <p style="font-size:13px;color:#333;margin-top:8px;">{job['jd'][:220]}...</p>
        </div>
        """)

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">
        <h2>🤖 Today's Robotics / ROS Job Matches</h2>
        <p>{len(new_jobs)} <b>new</b> listings since yesterday's scan (already-seen jobs are never repeated).</p>
        {dashboard_link_html}
        {''.join(rows)}
        <p style="color:#888;font-size:12px;margin-top:24px;">
            Sent automatically by your Robotics Job Bot &middot; runs daily at 8:00 PM IST &middot;
            {'<a href="' + DASHBOARD_URL + '">View full dashboard</a>' if DASHBOARD_URL else ''}
        </p>
    </body>
    </html>
    """


def send_email(html_body: str, new_job_count: int):
    subject = f"🤖 {new_job_count} New Robotics/ROS Matches — Daily Digest" if new_job_count else "🤖 No new Robotics/ROS matches today"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def main():
    print("Loading existing job store...")
    existing_store = load_existing_store()
    print(f"{len(existing_store)} jobs already on file.")

    print("Searching for jobs...")
    raw_jobs = collect_all_jobs()
    print(f"Found {len(raw_jobs)} listings in this scan (pre-dedup against history).")

    updated_store, new_jobs = merge_and_find_new(raw_jobs, existing_store)
    print(f"{len(new_jobs)} are genuinely new (not seen on a previous day).")

    write_jobs_json(updated_store)

    html = build_email_html(new_jobs)
    send_email(html, len(new_jobs))
    print("Email sent successfully.")


if __name__ == "__main__":
    main()
