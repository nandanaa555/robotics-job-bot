"""
Daily Robotics/ROS Job Search Bot
----------------------------------
Searches for robotics/ROS-related jobs using the Jooble API (free tier)
and emails a formatted digest via Gmail SMTP.

Runs automatically every day via GitHub Actions (see .github/workflows/daily-job-search.yml).
"""

import os
import json
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

# ---------------------------------------------------------------------------
# SECRETS — pulled from GitHub Actions repo secrets, never hardcode these
# ---------------------------------------------------------------------------

JOOBLE_API_KEY = os.environ["JOOBLE_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

JOOBLE_URL = f"https://jooble.org/api/{JOOBLE_API_KEY}"


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
    """Search every keyword, dedupe by job link, optionally filter by salary."""
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


def build_email_html(jobs: list[dict]) -> str:
    if not jobs:
        return "<p>No new matching jobs found today. Check back tomorrow!</p>"

    rows = []
    for job in jobs:
        title = job.get("title", "Untitled role")
        company = job.get("company", "Unknown company")
        location = job.get("location", "")
        salary = job.get("salary") or "Not listed"
        link = job.get("link", "#")
        snippet = (job.get("snippet") or "")[:220]

        rows.append(f"""
        <div style="margin-bottom:18px;padding:14px;border:1px solid #ddd;border-radius:8px;">
            <a href="{link}" style="font-size:16px;font-weight:bold;text-decoration:none;color:#1a73e8;">{title}</a>
            <div style="color:#555;font-size:14px;margin-top:4px;">{company} &middot; {location}</div>
            <div style="color:#555;font-size:13px;margin-top:2px;">💰 {salary}</div>
            <p style="font-size:13px;color:#333;margin-top:8px;">{snippet}...</p>
        </div>
        """)

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">
        <h2>🤖 Today's Robotics / ROS Job Matches</h2>
        <p>{len(jobs)} new listings found across your search keywords.</p>
        {''.join(rows)}
        <p style="color:#888;font-size:12px;margin-top:24px;">
            Sent automatically by your Robotics Job Bot &middot; runs daily at 8:00 PM IST
        </p>
    </body>
    </html>
    """


def send_email(html_body: str, job_count: int):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 {job_count} Robotics/ROS Job Matches — Daily Digest"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def write_jobs_json(jobs: list[dict], path: str = "docs/jobs.json"):
    """
    Save jobs in a structured format the web dashboard can read:
    id, title, company, location, stipend, jd (description snippet), link, source, fetched_at
    """
    structured = []
    for i, job in enumerate(jobs):
        structured.append({
            "id": f"job-{i}",
            "title": job.get("title", "Untitled role"),
            "company": job.get("company", "Unknown company"),
            "location": job.get("location", ""),
            "stipend": job.get("salary") or "Not listed",
            "jd": job.get("snippet", ""),
            "link": job.get("link", "#"),
            "source": "Indeed/Jooble",
        })

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "jobs": structured,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(structured)} jobs to {path}")


def main():
    print("Searching for jobs...")
    jobs = collect_all_jobs()
    print(f"Found {len(jobs)} unique jobs.")

    write_jobs_json(jobs)

    html = build_email_html(jobs)
    send_email(html, len(jobs))
    print("Email sent successfully.")


if __name__ == "__main__":
    main()
