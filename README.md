# Robotics Job Bot

Automated job discovery and resume tailoring for robotics/ROS roles. Scans job boards daily, surfaces results in a web dashboard, and generates a tailored one-page resume for any listing on demand.

Runs entirely on free infrastructure — GitHub Actions for automation, GitHub Pages for the dashboard. No server or paid hosting required.

## Features

- **Daily automated job search** — scans for robotics/ROS 2 roles every day at 8:00 PM IST via GitHub Actions
- **No repeats, ever** — every job is fingerprinted by its link; once seen, it's never emailed or re-shown as "new" again. The dashboard accumulates a running history of everything found across all days.
- **Web dashboard** — browse the full job history with stipend, job description, and apply links, hosted free on GitHub Pages
- **Mark jobs as applied** — check a job off once you've applied; it dims in the list and can be filtered out with "hide applied"
- **One-click tailored resumes** — generates a one-page PDF resume reordered to highlight the projects/skills most relevant to a specific job, delivered by email
- **Editable resume data** — your resume is stored as structured data (`resume_data.json`), pre-loaded from your real resume, and editable anytime from the dashboard or directly on GitHub
- **Email digests with a dashboard link** — daily summary of only the new matches, with a button straight to the dashboard

## How it works

| Component | Description |
|---|---|
| `job_search.py` | Queries the Jooble API for matching jobs, writes results to `docs/jobs.json`, and emails a digest |
| `generate_resume.py` | Scores your projects/skills against a job description and renders a tailored one-page PDF |
| `resume_data.json` | Single source of truth for your resume content |
| `docs/index.html` | Static dashboard — reads job data, lets you edit your resume, and triggers resume generation |
| `.github/workflows/daily-job-search.yml` | Scheduled workflow, runs the search daily |
| `.github/workflows/generate-resume.yml` | On-demand workflow, triggered from the dashboard or manually |

**Data source note:** job search currently covers Indeed and Jooble (which aggregates several boards). LinkedIn and Google don't offer a free public jobs API, so they aren't included.

**Resume tailoring note:** matching is keyword-based (no LLM), so it's instant and free — it reorders existing content rather than rewriting it.

## Setup

### Prerequisites
- A GitHub account
- A Gmail account
- A free [Jooble API key](https://jooble.org/api/about)

### 1. Get a Jooble API key
Sign up at [jooble.org/api/about](https://jooble.org/api/about) — free, no credit card required.

### 2. Create a Gmail App Password
Requires 2-Step Verification enabled on your Google account.
Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create a password for "Mail". This is a 16-character code, distinct from your regular Gmail password.

### 3. Configure repository secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `JOOBLE_API_KEY` | API key from step 1 |
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | App password from step 2 |
| `RECIPIENT_EMAIL` | Address to receive digests and tailored resumes |

### 4. Enable GitHub Pages
**Settings → Pages** → Source: `Deploy from a branch` → Branch: `main`, folder: `/docs` → Save.

The dashboard will be live at `https://<your-username>.github.io/robotics-job-bot/` within a couple of minutes.

### 5. Create a Personal Access Token for the dashboard
The dashboard reads/writes your resume and triggers workflows via direct calls to the GitHub API from your browser — no third-party server is involved.

Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new):
- Repository access: this repository only
- Permissions: `Contents: Read and write`, `Actions: Read and write`
- Generate and copy the token

Open the dashboard, click **⚙ Settings**, enter your GitHub username, repo name, and token, then **Save settings**.

> The token is stored only in your browser's local storage. It is never transmitted anywhere except directly to GitHub's API.

### 6. Verify the setup
- **Actions** tab → `Daily Robotics Job Search` → **Run workflow** → wait ~1 minute → refresh the dashboard to confirm jobs appear
- On the dashboard, click **Generate tailored resume** on any listing → check your email for the PDF

Once verified, the system runs unattended — daily scans populate the dashboard automatically.

## Usage

**Browsing jobs:** each dashboard card shows title, company, location, stipend, and an expandable job description, with a link to the original listing. The dashboard shows your entire job history, not just today's batch — a "hide applied" toggle lets you focus on what's still open.

**Marking a job as applied:** check the "applied" box on any card. It saves immediately to `docs/jobs.json` on GitHub, dims the card, and persists across all future dashboard visits.

**Generating a tailored resume:** click **Generate tailored resume** on any job card. The system reorders your projects and skill categories by relevance to that job's description and emails a one-page PDF within about a minute.

**Updating your resume:** click **Load resume** to pull the current version from GitHub, **Edit resume (JSON)** to make changes, then **Save to GitHub**. All future tailored resumes use the updated version immediately.

## Configuration

Search parameters are defined at the top of `job_search.py`:

```python
SEARCH_KEYWORDS = [...]      # terms to search for
LOCATION = "..."             # city, "India", or "remote"
ONLY_SHOW_JOBS_WITH_SALARY_LISTED = False
MAX_RESULTS_PER_KEYWORD = 10
```

Edit and push — no workflow changes required.

## Limitations

- Job coverage is limited to Indeed/Jooble; no LinkedIn or Google Jobs integration (no free API available for either)
- Resume tailoring uses keyword matching, not generative rewriting
- GitHub's Actions scheduler can run a few minutes behind schedule under load
- If your repository's default branch isn't `main`, update the `ref: 'main'` reference in `docs/index.html`'s `triggerResumeGeneration` function

## Possible extensions

AI-generated (rather than reordered) resume content is possible using the Claude API, at the cost of a small per-generation API fee and requiring your own Anthropic API key.
