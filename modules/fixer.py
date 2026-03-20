"""Auto-fix on-page SEO issues via WordPress REST API using Claude."""
import anthropic
from rich.console import Console
from modules.wp import WPClient
from modules.db import get_conn
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_meta(title, content_snippet, field):
    prompt = f"""You are an SEO expert. Given this page title and content, write an optimized {field}.

Page title: {title}
Content snippet: {content_snippet[:500]}

Requirements:
- meta title: 50-60 characters, include primary keyword naturally
- meta description: 140-155 characters, compelling, include a call to action

Return ONLY the {field} text, nothing else."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def generate_alt_text(img_url):
    prompt = f"""Write a concise, descriptive alt text for an image at this URL: {img_url}
Based on the URL/filename, describe what the image likely shows.
Return ONLY the alt text (under 125 characters), nothing else."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def run_fixer(site_url, dry_run=True):
    console.print(f"\n[bold cyan]Fixing SEO issues on:[/bold cyan] {site_url}")
    if dry_run:
        console.print("[yellow]DRY RUN mode — no changes will be applied[/yellow]\n")

    wp = WPClient(site_url=site_url)
    conn = get_conn()
    c = conn.cursor()

    # Get unfixed issues from DB
    c.execute("""
        SELECT id, page_url, issue_type, issue_detail
        FROM audit_results
        WHERE site_url = ? AND fixed = 0
        AND issue_type IN ('missing_meta_description', 'missing_title', 'missing_alt_text')
    """, (site_url,))
    issues = c.fetchall()

    if not issues:
        console.print("[green]No fixable issues found. Run audit first.[/green]")
        conn.close()
        return

    try:
        posts = wp.get_all_posts()
        url_to_post = {p.get("link", ""): p for p in posts}
    except Exception as e:
        console.print(f"[red]WordPress API error: {e}[/red]")
        conn.close()
        return

    fixed_count = 0
    for issue in issues:
        issue_id, page_url, issue_type, detail = issue

        post = url_to_post.get(page_url)
        if not post:
            continue

        post_id = post.get("id")
        title = post.get("title", {}).get("rendered", "")
        content = post.get("content", {}).get("rendered", "")

        if issue_type == "missing_meta_description":
            new_desc = generate_meta(title, content, "meta description")
            console.print(f"[cyan]Meta description for '{title[:40]}':[/cyan]\n  {new_desc}\n")
            if not dry_run:
                wp.update_post(post_id, {"meta": {"_yoast_wpseo_metadesc": new_desc}})
                c.execute("UPDATE audit_results SET fixed = 1 WHERE id = ?", (issue_id,))
            fixed_count += 1

        elif issue_type == "missing_title":
            new_title = generate_meta(title, content, "meta title")
            console.print(f"[cyan]Meta title for '{title[:40]}':[/cyan]\n  {new_title}\n")
            if not dry_run:
                wp.update_post(post_id, {"meta": {"_yoast_wpseo_title": new_title}})
                c.execute("UPDATE audit_results SET fixed = 1 WHERE id = ?", (issue_id,))
            fixed_count += 1

    conn.commit()
    conn.close()

    status = "Would fix" if dry_run else "Fixed"
    console.print(f"\n[bold green]{status} {fixed_count} issues.[/bold green]")
    if dry_run:
        console.print("Run with [bold]--no-dry-run[/bold] to apply changes.")
