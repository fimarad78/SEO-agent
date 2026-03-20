"""Unified SEO report dashboard."""
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from modules.db import get_conn

console = Console()


def run_report(site_url):
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")

    # Audit summary
    issues = conn.execute(
        "SELECT issue_type, COUNT(*) as count, SUM(fixed) as fixed FROM audit_results WHERE site_url = ? GROUP BY issue_type",
        (site_url,)
    ).fetchall()

    # Published posts
    posts = conn.execute(
        "SELECT title, keyword, url, published_at FROM published_posts WHERE site_url = ? ORDER BY published_at DESC LIMIT 10",
        (site_url,)
    ).fetchall()

    # Rankings summary
    rankings = conn.execute(
        """SELECT keyword, position, clicks, impressions
           FROM rankings WHERE site_url = ? AND recorded_date = (
               SELECT MAX(recorded_date) FROM rankings WHERE site_url = ?
           )
           ORDER BY clicks DESC LIMIT 10""",
        (site_url, site_url)
    ).fetchall()

    # Backlinks
    backlinks = conn.execute(
        "SELECT status, COUNT(*) as count FROM backlink_outreach WHERE site_url = ? GROUP BY status",
        (site_url,)
    ).fetchall()

    conn.close()

    console.print(Panel(f"[bold]SEO Report — {site_url}[/bold]\n{today}", style="cyan"))

    # Issues
    if issues:
        t = Table(title="Audit Issues", show_lines=True)
        t.add_column("Issue Type", style="yellow")
        t.add_column("Total", justify="right")
        t.add_column("Fixed", justify="right", style="green")
        t.add_column("Remaining", justify="right", style="red")
        for row in issues:
            remaining = (row["count"] or 0) - (row["fixed"] or 0)
            t.add_row(row["issue_type"], str(row["count"]), str(row["fixed"] or 0), str(remaining))
        console.print(t)

    # Posts
    if posts:
        t = Table(title="Published Posts", show_lines=True)
        t.add_column("Title", style="cyan", max_width=40)
        t.add_column("Keyword", style="yellow")
        t.add_column("Published", style="white")
        for p in posts:
            t.add_row(p["title"][:40], p["keyword"], p["published_at"][:10])
        console.print(t)

    # Rankings
    if rankings:
        t = Table(title="Top Rankings (latest)", show_lines=True)
        t.add_column("Keyword", style="cyan", max_width=40)
        t.add_column("Position", justify="right", style="yellow")
        t.add_column("Clicks", justify="right")
        t.add_column("Impressions", justify="right")
        for r in rankings:
            t.add_row(r["keyword"][:40], f"{r['position']:.1f}", str(r["clicks"]), str(r["impressions"]))
        console.print(t)

    # Backlinks
    if backlinks:
        t = Table(title="Backlink Outreach", show_lines=True)
        t.add_column("Status", style="cyan")
        t.add_column("Count", justify="right")
        for b in backlinks:
            t.add_row(b["status"], str(b["count"]))
        console.print(t)

    if not any([issues, posts, rankings, backlinks]):
        console.print("[yellow]No data yet. Run audit, publish content, and monitor to populate the report.[/yellow]")
