"""
On-demand tailored resume generator.
----------------------------------------
Triggered manually (paste a job title + description), this:
  1. Scores your projects/skills against the job description text
  2. Reorders content so the most relevant stuff appears first
  3. Renders a clean one-page PDF
  4. Emails it to you

No AI/LLM call involved — pure keyword matching, so it's free and fast.
"""

import os
import re
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

with open(os.path.join(os.path.dirname(__file__), "resume_data.json")) as f:
    RESUME = json.load(f)

CANDIDATE = RESUME["candidate"]
CAREER_OBJECTIVE = RESUME["career_objective"]
EDUCATION = RESUME["education"]
SKILLS = RESUME["skills"]
INTERNSHIP = RESUME["internship"]
PROJECTS = RESUME["projects"]

# ---------------------------------------------------------------------------
# Inputs (from GitHub Actions workflow_dispatch, or env vars if run locally)
# ---------------------------------------------------------------------------

JOB_TITLE = os.environ.get("JOB_TITLE", "").strip()
COMPANY = os.environ.get("COMPANY", "").strip()
JOB_DESCRIPTION = os.environ.get("JOB_DESCRIPTION", "").strip()

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

OUTPUT_PDF = "tailored_resume.pdf"


def score_text_against_keywords(text: str, keywords: list[str]) -> int:
    """Count how many of the given keywords appear in text (case-insensitive)."""
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        # strip parenthetical version numbers etc. for a looser match, e.g. "ROS 2 (Jazzy)" -> "ROS 2"
        core = re.sub(r"\(.*?\)", "", kw).strip().lower()
        if core and core in text_lower:
            score += 1
    return score


def rank_projects(job_text: str) -> list[dict]:
    ranked = sorted(PROJECTS, key=lambda p: score_text_against_keywords(job_text, p["tech"]), reverse=True)
    # Keep it to a one-pager: top 3 projects
    return ranked[:3]


def rank_skill_categories(job_text: str) -> list[tuple]:
    scored = [
        (category, skills, score_text_against_keywords(job_text, skills))
        for category, skills in SKILLS.items()
    ]
    scored.sort(key=lambda x: x[2], reverse=True)
    return [(cat, skills) for cat, skills, _ in scored]


def build_pdf(ranked_projects, ranked_skills, job_text: str):
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Title"], fontSize=18, alignment=TA_CENTER, spaceAfter=2)
    tagline_style = ParagraphStyle("Tagline", parent=styles["Normal"], fontSize=9.5, alignment=TA_CENTER,
                                    textColor="#444444", spaceAfter=2)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER,
                                    spaceAfter=10)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=11.5, spaceBefore=8,
                                    spaceAfter=4, textColor="#1a3d7c")
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.3, leading=12.5)
    bullet_style = ParagraphStyle("Bullet", parent=body_style, leftIndent=12, spaceAfter=3)
    small_bold = ParagraphStyle("SmallBold", parent=body_style, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(
        OUTPUT_PDF, pagesize=LETTER,
        topMargin=0.45 * inch, bottomMargin=0.4 * inch,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
    )
    story = []

    story.append(Paragraph(CANDIDATE["name"], name_style))
    story.append(Paragraph(CANDIDATE["tagline"], tagline_style))
    contact_line = (f'{CANDIDATE["phone"]} | {CANDIDATE["email"]} | '
                     f'{CANDIDATE["linkedin"]} | {CANDIDATE["github"]}')
    story.append(Paragraph(contact_line, contact_style))
    story.append(HRFlowable(width="100%", thickness=0.7, color="#1a3d7c"))

    # Tailored opening line if a job title was given
    story.append(Paragraph("Career Objective", heading_style))
    objective = CAREER_OBJECTIVE
    if JOB_TITLE:
        objective = (f"Seeking the {JOB_TITLE} role" + (f" at {COMPANY}" if COMPANY else "") +
                      " to apply hands-on robotics and ROS 2 experience. " + CAREER_OBJECTIVE)
    story.append(Paragraph(objective, body_style))

    # Skills (most relevant categories first)
    story.append(Paragraph("Technical Skills", heading_style))
    for category, skills in ranked_skills:
        story.append(Paragraph(f"<b>{category}:</b> {', '.join(skills)}", body_style))

    # Education (compact)
    story.append(Paragraph("Education", heading_style))
    for edu in EDUCATION:
        story.append(Paragraph(f'<b>{edu["degree"]}</b> — {edu["school"]} ({edu["detail"]})', body_style))

    # Internship
    story.append(Paragraph("Internship Experience", heading_style))
    story.append(Paragraph(
        f'<b>{INTERNSHIP["role"]}</b>, {INTERNSHIP["company"]}, {INTERNSHIP["location"]} '
        f'&nbsp;&mdash;&nbsp; {INTERNSHIP["dates"]}', small_bold))
    for b in INTERNSHIP["bullets"]:
        story.append(Paragraph(f"• {b}", bullet_style))
    story.append(Paragraph(f'<i>Technologies: {", ".join(INTERNSHIP["tech"])}</i>', body_style))

    # Projects (most relevant first, top 3 only, to fit one page)
    story.append(Paragraph("Projects", heading_style))
    for proj in ranked_projects:
        story.append(Paragraph(f'<b>{proj["title"]}</b> — {proj["status"]}', small_bold))
        for b in proj["bullets"]:
            story.append(Paragraph(f"• {b}", bullet_style))
        story.append(Paragraph(f'<i>Technologies: {", ".join(proj["tech"])}</i>', body_style))
        story.append(Spacer(1, 4))

    doc.build(story)


def send_email_with_attachment():
    subject_target = f"{JOB_TITLE}" + (f" at {COMPANY}" if COMPANY else "") if JOB_TITLE else "Tailored Resume"
    msg = MIMEMultipart()
    msg["Subject"] = f"📄 Tailored Resume — {subject_target}"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    body = (f"Here's your one-page resume tailored for: {JOB_TITLE or '(no title given)'}"
            f"{f' at {COMPANY}' if COMPANY else ''}.\n\n"
            "Projects and skills were reordered to highlight what best matches this job's description.\n"
            "Always give it a quick read before sending — automated tailoring isn't perfect!")
    msg.attach(MIMEText(body, "plain"))

    with open(OUTPUT_PDF, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename="Nandanaa_MS_Resume_Tailored.pdf")
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def main():
    job_text = f"{JOB_TITLE} {JOB_DESCRIPTION}"
    if not job_text.strip():
        print("[warn] No job title/description provided — using default resume ordering.")

    ranked_projects = rank_projects(job_text)
    ranked_skills = rank_skill_categories(job_text)

    build_pdf(ranked_projects, ranked_skills, job_text)
    print(f"PDF built: {OUTPUT_PDF}")

    send_email_with_attachment()
    print("Tailored resume emailed successfully.")


if __name__ == "__main__":
    main()
