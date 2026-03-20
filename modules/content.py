"""Generate and publish SEO-optimized blog posts using Claude."""
import anthropic
from rich.console import Console
from modules.wp import WPClient
from modules.db import get_conn
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def research_keyword(keyword, niche=""):
    prompt = f"""You are an expert SEO content strategist. Research the keyword: "{keyword}"
{f'The website niche is: {niche}' if niche else ''}

Provide:
1. Search intent (informational/commercial/transactional/navigational)
2. 5 related LSI keywords to include naturally
3. Top 5 questions people ask about this topic (for FAQ section)
4. Suggested content angle that would outrank competitors
5. Recommended word count

Format as JSON."""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def write_post(keyword, research, niche=""):
    prompt = f"""You are an expert SEO content writer. Write a comprehensive, SEO-optimized blog post.

Keyword: "{keyword}"
{f'Niche: {niche}' if niche else ''}
Research: {research}

Requirements:
- Compelling title with keyword near the start (50-60 chars)
- Meta description (140-155 chars)
- Introduction with keyword in first paragraph
- Use H2 and H3 subheadings with related keywords
- Include the LSI keywords naturally throughout
- Add a FAQ section with the top questions answered
- Strong conclusion with call to action
- Write in HTML format suitable for WordPress
- Minimum 1200 words, aim for 1500+
- Natural, engaging tone — not robotic

Return in this exact format:
TITLE: [your title]
META: [your meta description]
CONTENT:
[full HTML content]"""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def parse_post(raw):
    lines = raw.split("\n")
    title, meta, content_lines = "", "", []
    in_content = False
    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("META:"):
            meta = line.replace("META:", "").strip()
        elif line.startswith("CONTENT:"):
            in_content = True
        elif in_content:
            content_lines.append(line)
    return title, meta, "\n".join(content_lines)


def run_content(site_url, keyword, niche="", publish=True):
    console.print(f"\n[bold cyan]Generating post for keyword:[/bold cyan] '{keyword}'\n")

    console.print("[yellow]Researching keyword...[/yellow]")
    research = research_keyword(keyword, niche)

    console.print("[yellow]Writing post...[/yellow]")
    raw = write_post(keyword, research, niche)
    title, meta, content = parse_post(raw)

    console.print(f"\n[bold]Title:[/bold] {title}")
    console.print(f"[bold]Meta:[/bold] {meta}")
    console.print(f"[bold]Content length:[/bold] {len(content.split())} words\n")

    if not publish:
        console.print("[yellow]Draft mode — not publishing.[/yellow]")
        return {"title": title, "meta": meta, "content": content}

    console.print("[yellow]Publishing to WordPress...[/yellow]")
    wp = WPClient(site_url=site_url)
    post = wp.create_post(
        title=title,
        content=content,
        status="publish",
        meta={"_yoast_wpseo_metadesc": meta}
    )

    post_url = post.get("link", "")
    post_id = post.get("id")
    console.print(f"[bold green]Published![/bold green] {post_url}")

    conn = get_conn()
    conn.execute(
        "INSERT INTO published_posts (site_url, wp_post_id, title, keyword, url) VALUES (?, ?, ?, ?, ?)",
        (site_url, post_id, title, keyword, post_url)
    )
    conn.commit()
    conn.close()

    return post
