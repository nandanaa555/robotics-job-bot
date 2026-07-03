# Robotics/ROS Job Bot 🤖

- Scans job boards daily at **8:00 PM IST** for robotics/ROS roles (stipend, JD, apply link)
- Gives you a **web dashboard** (free, hosted on GitHub Pages) to browse them
- One click on any job generates a **tailored one-page resume PDF**, emailed to you
- Your resume lives in the repo as data — edit it anytime, from the dashboard or directly on GitHub

Runs entirely free: GitHub Actions (automation) + GitHub Pages (dashboard). No server, no laptop needed to stay on.

**Honest limitation:** job search currently covers **Indeed + Jooble** (Jooble aggregates several boards). LinkedIn and Google don't offer a free public jobs API, so they're not included — adding them would need paid/partner API access.

## One-time setup (~15 minutes)

### 1. Create the repo
Create a **new GitHub repo** named e.g. `robotics-job-bot`, and upload all files from this folder — keep the `.github/workflows/` and `docs/` folder structure exactly as-is.

### 2. Turn on GitHub Pages (for the dashboard)
Repo → **Settings → Pages** → under "Build and deployment", set **Source: Deploy from a branch**, **Branch: main, folder: `/docs`** → Save.
Your dashboard will be live at `https://<your-username>.github.io/robotics-job-bot/` within a minute or two.

### 3. Get a free Jooble API key
https://jooble.org/api/about — sign up, no credit card, get an API key.

### 4. Create a Gmail App Password
https://myaccount.google.com/apppasswords (needs 2-Step Verification on). Create one for "Mail" — a 16-character code. **Not your real Gmail password.**

### 5. Add repo secrets
**Settings → Secrets and variables → Actions → New repository secret.** Add these four:

| Secret name | Value |
|---|---|
| `JOOBLE_API_KEY` | from step 3 |
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASSWORD` | from step 4 |
| `RECIPIENT_EMAIL` | where digests/resumes get sent (can be same Gmail) |

### 6. Create a GitHub Personal Access Token (for the dashboard)
The dashboard needs to read/write files and trigger workflows on your behalf — this happens **entirely in your browser**, nothing goes through a third-party server.

- Go to https://github.com/settings/personal-access-tokens/new
- Name it e.g. "Job Bot Dashboard"
- **Repository access:** only this repo
- **Permissions:** `Contents: Read and write`, `Actions: Read and write`
- Generate, copy the token (starts with `github_pat_...`)

### 7. Open your dashboard
Go to `https://<your-username>.github.io/robotics-job-bot/`, click **⚙ Settings**, enter your GitHub username, repo name, and the token from step 6, click **Save settings**.

⚠️ The token is stored **only in your browser's local storage** — it never leaves your device except for direct calls to GitHub's own API. Don't paste it anywhere else, and don't use this dashboard on a shared/public computer.

### 8. Test it
- **Actions** tab → **Daily Robotics Job Search** → **Run workflow** (manual trigger) → wait ~1 min → refresh your dashboard, jobs should appear.
- On the dashboard, click **Generate tailored resume** on any job → check your email in ~1 minute for the PDF.

### 9. Done
From now on, jobs refresh automatically every day at 8pm IST, and the dashboard always shows the latest scan. No further setup needed.

## Using the dashboard

- **Job cards** show title, company, location, stipend, and job description (expand with "Job description"), plus an **Open listing** link.
- **Generate tailored resume** — reorders your projects/skills by relevance to that job's description and emails you a one-page PDF. No AI involved — pure keyword matching, instant, free.
- **Your Resume** section — click **Load resume** to pull your current data from GitHub, **Edit resume (JSON)** to update it (add a new project, tweak skills, etc.), then **Save to GitHub**. Every future tailored resume uses the updated version immediately.

**Want AI-rewritten bullet points** instead of just reordering? Possible with the Claude API, but needs your own Anthropic API key and costs a few cents per resume — let me know if you want that upgrade.

## Customizing the search

Open `job_search.py`:
- `SEARCH_KEYWORDS` — add/remove search terms
- `LOCATION` — city, `"India"`, or `"remote"`
- `ONLY_SHOW_JOBS_WITH_SALARY_LISTED` — `True` to hide listings with no salary info
- `MAX_RESULTS_PER_KEYWORD` — results per keyword

Commit and push — no workflow file changes needed.

## Notes
- GitHub Actions free tier: 2,000 min/month — this uses seconds/day, nowhere near the limit.
- GitHub's scheduler can run a few minutes late under load — normal, not a bug.
- If your repo's default branch isn't `main`, edit the `ref: 'main'` line in `docs/index.html`'s `triggerResumeGeneration` function to match.
- Dashboard reads `docs/jobs.json` (public, no auth needed) but reads/writes your resume and triggers workflows via the GitHub API using your personal token.
