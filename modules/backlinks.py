"""Backlink builder - find opportunities and send outreach emails."""
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import anthropic
from rich.console import Console
from modules.db import get_conn
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SERP_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def find_opportunities_serp(niche, site_url):
    """Find backlink opportunities via SerpAPI."""
    if not SERP_API_KEY:
        console.print("[yellow]No SerpAPI key — using manual opportunity list.[/yellow]")
        return []

    queries = [
        f'"{niche}" "write for us"',
        f'"{niche}" "submit a guest post"',
        f'"{niche}" "resource page"',
        f'"{niche}" "useful links"',
    ]

    opportunities = []
    for q in queries:
        try:
            r = requests.get("https://serpapi.com/search", params={
                "q": q,
                "api_key": SERP_API_KEY,
                "num": 10
            }, timeout=15)
            data = r.json()
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                snippet = result.get("snippet", "")
                if link and site_url not in link:
                    opportunities.append({"url": link, "snippet": snippet, "query": q})
        except Exception as e:
            console.print(f"[red]SerpAPI error: {e}[/red]")

    return opportunities


def write_outreach_email(target_url, target_snippet, your_site, your_name, niche):
    prompt = f"""Write a personalized, professional backlink outreach email.

Target site: {target_url}
What their page is about: {target_snippet}
Your website: {your_site}
Your name: {your_name}
Niche: {niche}

Guidelines:
- Be genuine and specific to their site (not generic)
- Explain why your content would benefit their readers
- Keep it short (under 150 words)
- Don't be pushy or desperate
- Natural, human tone

Return ONLY the email body (no subject line), starting with the greeting."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def write_subject_line(target_url, niche):
    prompt = f"""Write a short, compelling email subject line for a backlink outreach email to {target_url} in the {niche} niche.
Return ONLY the subject line, nothing else. Under 60 characters."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


def run_backlinks(site_url, niche, your_name="SEO Agent", send=False):
    console.print(f"\n[bold cyan]Finding backlink opportunities for:[/bold cyan] {site_url}\n")

    opportunities = find_opportunities_serp(niche, site_url)

    if not opportunities:
        console.print("[yellow]No opportunities found via SerpAPI. Add your SERP_API_KEY to .env to enable search.[/yellow]")
        console.print("\nYou can manually add opportunities to the database and re-run.")
        return []

    conn = get_conn()
    results = []

    for opp in opportunities[:10]:  # Process top 10
        target_url = opp["url"]
        snippet = opp.get("snippet", "")

        console.print(f"\n[cyan]Opportunity:[/cyan] {target_url}")

        email_body = write_outreach_email(target_url, snippet, site_url, your_name, niche)
        subject = write_subject_line(target_url, niche)

        console.print(f"[bold]Subject:[/bold] {subject}")
        console.print(f"[bold]Email:[/bold]\n{email_body}\n")

        conn.execute(
            "INSERT INTO backlink_outreach (site_url, target_url, status) VALUES (?, ?, 'draft')",
            (site_url, target_url)
        )

        results.append({"url": target_url, "subject": subject, "body": email_body})

    conn.commit()
    conn.close()

    if send and SMTP_USER:
        console.print("[yellow]Sending emails is enabled but requires contact emails for each target.[/yellow]")
        console.print("Update the backlink_outreach table with contact_email and re-run with --send.")

    console.print(f"\n[bold green]Found {len(results)} opportunities. Outreach emails drafted.[/bold green]")
    return results
