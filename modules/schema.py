"""Inject JSON-LD schema markup into WordPress posts."""
import json
import anthropic
from bs4 import BeautifulSoup
from rich.console import Console
from modules.wp import WPClient
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_schema(post):
    title = post.get("title", {}).get("rendered", "")
    content = post.get("content", {}).get("rendered", "")
    url = post.get("link", "")
    date = post.get("date", "")

    # Extract plain text
    soup = BeautifulSoup(content, "lxml")
    text = soup.get_text(separator=" ", strip=True)[:1000]

    # Extract FAQ questions from content
    faqs = []
    for tag in soup.find_all(["h2", "h3"]):
        if "?" in tag.get_text():
            question = tag.get_text(strip=True)
            answer_tag = tag.find_next_sibling(["p", "div"])
            answer = answer_tag.get_text(strip=True)[:300] if answer_tag else ""
            if answer:
                faqs.append({"question": question, "answer": answer})

    prompt = f"""Generate appropriate JSON-LD schema markup for this blog post.

Title: {title}
URL: {url}
Published: {date}
Content excerpt: {text}
FAQ pairs found: {json.dumps(faqs[:5])}

Include:
1. Article schema (always)
2. FAQPage schema if there are FAQ pairs
3. BreadcrumbList schema

Return a single valid JSON-LD <script> block, nothing else."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def run_schema(site_url, dry_run=True):
    console.print(f"\n[bold cyan]Adding schema markup to:[/bold cyan] {site_url}")
    if dry_run:
        console.print("[yellow]DRY RUN mode — no changes applied[/yellow]\n")

    wp = WPClient(site_url=site_url)

    try:
        posts = wp.get_all_posts()
    except Exception as e:
        console.print(f"[red]WordPress API error: {e}[/red]")
        return

    updated = 0
    for post in posts:
        title = post.get("title", {}).get("rendered", "")
        content = post.get("content", {}).get("rendered", "")

        # Skip if already has schema
        if "application/ld+json" in content:
            continue

        console.print(f"[yellow]Generating schema for:[/yellow] {title[:60]}")
        schema_block = generate_schema(post)

        new_content = content + "\n\n" + schema_block

        if not dry_run:
            post_type = "posts" if post.get("type") == "post" else "pages"
            if post_type == "posts":
                wp.update_post(post["id"], {"content": new_content})
            else:
                wp.update_page(post["id"], {"content": new_content})

        console.print(f"[green]Schema ready for:[/green] {title[:60]}\n")
        updated += 1

    action = "Would update" if dry_run else "Updated"
    console.print(f"\n[bold green]{action} {updated} posts with schema markup.[/bold green]")
