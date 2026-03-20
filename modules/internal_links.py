"""Auto-add internal links between related posts."""
import re
import anthropic
from bs4 import BeautifulSoup
from rich.console import Console
from modules.wp import WPClient
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def find_link_opportunities(posts):
    """Ask Claude to identify internal linking opportunities."""
    post_summaries = []
    for p in posts[:50]:  # Limit to 50 posts for context
        title = p.get("title", {}).get("rendered", "")
        url = p.get("link", "")
        post_summaries.append(f"- ID {p['id']}: '{title}' ({url})")

    prompt = f"""You are an SEO expert. Analyze these blog posts and identify internal linking opportunities.

Posts:
{chr(10).join(post_summaries)}

For each pair that should be linked, provide:
- Source post ID
- Target post ID
- Suggested anchor text (3-5 words, natural)
- Reason

Return as a JSON array of objects with keys: source_id, target_id, anchor_text, reason
Only suggest links that genuinely make sense contextually. Max 20 suggestions."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        text = msg.content[0].text.strip()
        # Extract JSON from response
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


def insert_link(content, anchor_text, target_url):
    """Insert a link into content at first occurrence of anchor text phrase."""
    if target_url in content:
        return content, False  # Already linked

    pattern = re.compile(re.escape(anchor_text), re.IGNORECASE)
    link_html = f'<a href="{target_url}">{anchor_text}</a>'
    new_content, count = pattern.subn(link_html, content, count=1)
    return new_content, count > 0


def run_internal_links(site_url, dry_run=True):
    console.print(f"\n[bold cyan]Building internal links for:[/bold cyan] {site_url}")
    if dry_run:
        console.print("[yellow]DRY RUN mode — no changes applied[/yellow]\n")

    wp = WPClient(site_url=site_url)

    try:
        posts = wp.get_all_posts()
    except Exception as e:
        console.print(f"[red]WordPress API error: {e}[/red]")
        return

    console.print(f"[yellow]Analyzing {len(posts)} posts for linking opportunities...[/yellow]")
    suggestions = find_link_opportunities(posts)

    if not suggestions:
        console.print("[yellow]No linking opportunities found.[/yellow]")
        return

    id_to_post = {p["id"]: p for p in posts}
    applied = 0

    for s in suggestions:
        source = id_to_post.get(s.get("source_id"))
        target = id_to_post.get(s.get("target_id"))
        if not source or not target:
            continue

        anchor = s.get("anchor_text", "")
        target_url = target.get("link", "")
        source_content = source.get("content", {}).get("rendered", "")

        new_content, inserted = insert_link(source_content, anchor, target_url)

        console.print(f"[cyan]Link:[/cyan] '{source.get('title',{}).get('rendered','')}' → '{target.get('title',{}).get('rendered','')}' (anchor: '{anchor}')")

        if inserted and not dry_run:
            wp.update_post(source["id"], {"content": new_content})
            applied += 1
        elif inserted:
            applied += 1

    action = "Would add" if dry_run else "Added"
    console.print(f"\n[bold green]{action} {applied} internal links.[/bold green]")
