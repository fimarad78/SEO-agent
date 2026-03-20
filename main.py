#!/usr/bin/env python3
"""SEO Agent - Fully autonomous SEO optimization powered by Claude."""
import click
from rich.console import Console
from modules.db import init_db

console = Console()


@click.group()
def cli():
    """SEO Agent - Automate your entire SEO workflow with Claude AI."""
    init_db()


@cli.command()
@click.option("--site", required=True, help="WordPress site URL (e.g. https://yoursite.com)")
def audit(site):
    """Crawl and audit your site for SEO issues."""
    from modules.auditor import run_audit
    run_audit(site)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--dry-run/--no-dry-run", default=True, help="Preview changes without applying (default: dry-run)")
def fix(site, dry_run):
    """Auto-fix on-page SEO issues using Claude."""
    from modules.fixer import run_fixer
    run_fixer(site, dry_run=dry_run)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--keyword", required=True, help="Target keyword to write about")
@click.option("--niche", default="", help="Your website niche (e.g. 'personal finance')")
@click.option("--draft/--publish", default=False, help="Publish immediately or save as draft (default: publish)")
def publish(site, keyword, niche, draft):
    """Generate and publish an SEO-optimized blog post."""
    from modules.content import run_content
    run_content(site, keyword, niche=niche, publish=not draft)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--niche", required=True, help="Your website niche (e.g. 'fitness')")
@click.option("--name", default="The Team", help="Your name for outreach emails")
@click.option("--send/--no-send", default=False, help="Send outreach emails (default: draft only)")
def backlinks(site, niche, name, send):
    """Find backlink opportunities and draft outreach emails."""
    from modules.backlinks import run_backlinks
    run_backlinks(site, niche, your_name=name, send=send)


@cli.command("internal-links")
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--dry-run/--no-dry-run", default=True, help="Preview without applying (default: dry-run)")
def internal_links(site, dry_run):
    """Add internal links between related posts."""
    from modules.internal_links import run_internal_links
    run_internal_links(site, dry_run=dry_run)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--dry-run/--no-dry-run", default=True, help="Preview without applying (default: dry-run)")
def schema(site, dry_run):
    """Inject JSON-LD schema markup into posts."""
    from modules.schema import run_schema
    run_schema(site, dry_run=dry_run)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL (must be verified in Search Console)")
def monitor(site):
    """Fetch and track keyword rankings from Google Search Console."""
    from modules.monitor import run_monitor
    run_monitor(site)


@cli.command()
@click.option("--site", required=True, help="WordPress site URL")
def report(site):
    """Show unified SEO dashboard report."""
    from modules.reporter import run_report
    run_report(site)


@cli.command("run-all")
@click.option("--site", required=True, help="WordPress site URL")
@click.option("--keyword", default="", help="Keyword to publish a post about")
@click.option("--niche", default="", help="Website niche")
@click.option("--dry-run/--no-dry-run", default=True, help="Preview fixes without applying")
def run_all(site, keyword, niche, dry_run):
    """Run the full autonomous SEO workflow."""
    console.print("\n[bold magenta]Running full SEO agent workflow...[/bold magenta]\n")

    from modules.auditor import run_audit
    from modules.fixer import run_fixer
    from modules.content import run_content
    from modules.internal_links import run_internal_links
    from modules.schema import run_schema
    from modules.monitor import run_monitor
    from modules.reporter import run_report

    console.rule("[bold]Step 1: Audit[/bold]")
    run_audit(site)

    console.rule("[bold]Step 2: Fix Issues[/bold]")
    run_fixer(site, dry_run=dry_run)

    if keyword:
        console.rule("[bold]Step 3: Publish Content[/bold]")
        run_content(site, keyword, niche=niche, publish=not dry_run)

    console.rule("[bold]Step 4: Internal Links[/bold]")
    run_internal_links(site, dry_run=dry_run)

    console.rule("[bold]Step 5: Schema Markup[/bold]")
    run_schema(site, dry_run=dry_run)

    console.rule("[bold]Step 6: Rankings[/bold]")
    run_monitor(site)

    console.rule("[bold]Step 7: Report[/bold]")
    run_report(site)

    console.print("\n[bold green]SEO agent run complete![/bold green]")


if __name__ == "__main__":
    cli()
