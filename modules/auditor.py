"""SEO Auditor - crawls WordPress site and reports SEO issues."""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from rich.console import Console
from rich.table import Table
from modules.wp import WPClient
from modules.db import get_conn, init_db

console = Console()


def audit_page(url, html, site_url):
    issues = []
    soup = BeautifulSoup(html, "lxml")

    # Meta title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        issues.append(("missing_title", "Page has no <title> tag"))
    elif len(title) < 30:
        issues.append(("short_title", f"Title too short ({len(title)} chars): '{title}'"))
    elif len(title) > 60:
        issues.append(("long_title", f"Title too long ({len(title)} chars): '{title}'"))

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc = meta_desc.get("content", "").strip() if meta_desc else ""
    if not desc:
        issues.append(("missing_meta_description", "No meta description found"))
    elif len(desc) < 50:
        issues.append(("short_meta_description", f"Meta description too short ({len(desc)} chars)"))
    elif len(desc) > 160:
        issues.append(("long_meta_description", f"Meta description too long ({len(desc)} chars)"))

    # H1
    h1s = soup.find_all("h1")
    if not h1s:
        issues.append(("missing_h1", "No H1 tag found on page"))
    elif len(h1s) > 1:
        issues.append(("multiple_h1", f"Multiple H1 tags found ({len(h1s)})"))

    # Images without alt text
    images = soup.find_all("img")
    for img in images:
        src = img.get("src", "")
        alt = img.get("alt", "").strip()
        if not alt:
            issues.append(("missing_alt_text", f"Image missing alt text: {src[:80]}"))

    # Canonical tag
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if not canonical:
        issues.append(("missing_canonical", "No canonical tag found"))

    # Broken internal links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)
        if parsed.netloc and site_url in parsed.netloc:
            try:
                r = requests.head(full_url, timeout=5, allow_redirects=True)
                if r.status_code >= 400:
                    issues.append(("broken_link", f"Broken link ({r.status_code}): {full_url}"))
            except Exception:
                pass

    return issues


def check_technical(site_url):
    issues = []
    base = site_url.rstrip("/")

    # robots.txt
    try:
        r = requests.get(f"{base}/robots.txt", timeout=10)
        if r.status_code != 200:
            issues.append(("missing_robots_txt", "robots.txt not found or not accessible"))
    except Exception:
        issues.append(("missing_robots_txt", "Could not reach robots.txt"))

    # sitemap
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"]:
        try:
            r = requests.get(f"{base}{path}", timeout=10)
            if r.status_code == 200:
                break
        except Exception:
            pass
    else:
        issues.append(("missing_sitemap", "No sitemap.xml found"))

    return issues


def run_audit(site_url):
    init_db()
    console.print(f"\n[bold cyan]Auditing:[/bold cyan] {site_url}\n")
    wp = WPClient(site_url=site_url)
    all_issues = []

    # Technical checks
    console.print("[yellow]Checking technical SEO...[/yellow]")
    tech_issues = check_technical(site_url)
    for issue_type, detail in tech_issues:
        all_issues.append({"url": site_url, "type": issue_type, "detail": detail})

    # Page-level checks
    console.print("[yellow]Fetching posts and pages...[/yellow]")
    try:
        posts = wp.get_all_posts()
    except Exception as e:
        console.print(f"[red]Could not connect to WordPress API: {e}[/red]")
        return []

    console.print(f"[yellow]Auditing {len(posts)} pages/posts...[/yellow]")
    for post in posts:
        url = post.get("link", "")
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15)
            page_issues = audit_page(url, r.text, site_url)
            for issue_type, detail in page_issues:
                all_issues.append({"url": url, "type": issue_type, "detail": detail})
        except Exception as e:
            all_issues.append({"url": url, "type": "fetch_error", "detail": str(e)})

    # Save to DB
    conn = get_conn()
    c = conn.cursor()
    for issue in all_issues:
        c.execute(
            "INSERT INTO audit_results (site_url, page_url, issue_type, issue_detail) VALUES (?, ?, ?, ?)",
            (site_url, issue["url"], issue["type"], issue["detail"])
        )
    conn.commit()
    conn.close()

    # Display results
    table = Table(title=f"SEO Audit: {site_url}", show_lines=True)
    table.add_column("URL", style="cyan", max_width=50)
    table.add_column("Issue Type", style="yellow")
    table.add_column("Detail", style="white", max_width=60)

    for issue in all_issues:
        table.add_row(issue["url"][:50], issue["type"], issue["detail"][:60])

    console.print(table)
    console.print(f"\n[bold]Total issues found: {len(all_issues)}[/bold]")
    return all_issues
