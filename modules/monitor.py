"""Monitor rankings via Google Search Console API."""
import os
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from modules.db import get_conn
from config import GOOGLE_CREDENTIALS_FILE

console = Console()


def get_gsc_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
    token_file = "token.json"
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("searchconsole", "v1", credentials=creds)


def fetch_rankings(site_url, days=28):
    service = get_gsc_service()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = service.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query", "page"],
            "rowLimit": 500,
            "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]
        }
    ).execute()

    return response.get("rows", [])


def run_monitor(site_url):
    console.print(f"\n[bold cyan]Fetching rankings for:[/bold cyan] {site_url}\n")

    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        console.print(f"[red]Google credentials not found at: {GOOGLE_CREDENTIALS_FILE}[/red]")
        console.print("\nTo set up Google Search Console:")
        console.print("1. Go to Google Cloud Console → Create project")
        console.print("2. Enable Search Console API")
        console.print("3. Create OAuth2 credentials → Download as credentials.json")
        console.print("4. Place credentials.json in this folder")
        return

    try:
        rows = fetch_rankings(site_url)
    except Exception as e:
        console.print(f"[red]Error fetching rankings: {e}[/red]")
        return

    if not rows:
        console.print("[yellow]No ranking data found. Make sure your site is verified in Google Search Console.[/yellow]")
        return

    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")

    for row in rows:
        keys = row.get("keys", [])
        keyword = keys[0] if len(keys) > 0 else ""
        page = keys[1] if len(keys) > 1 else ""
        conn.execute(
            "INSERT INTO rankings (site_url, keyword, page_url, clicks, impressions, ctr, position, recorded_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (site_url, keyword, page, row.get("clicks", 0), row.get("impressions", 0), row.get("ctr", 0), row.get("position", 0), today)
        )

    conn.commit()
    conn.close()

    # Display top 20
    table = Table(title=f"Top Rankings: {site_url}", show_lines=True)
    table.add_column("Keyword", style="cyan", max_width=40)
    table.add_column("Position", style="yellow", justify="right")
    table.add_column("Clicks", justify="right")
    table.add_column("Impressions", justify="right")
    table.add_column("CTR", justify="right")

    for row in rows[:20]:
        keys = row.get("keys", [])
        keyword = keys[0] if keys else ""
        table.add_row(
            keyword[:40],
            f"{row.get('position', 0):.1f}",
            str(row.get("clicks", 0)),
            str(row.get("impressions", 0)),
            f"{row.get('ctr', 0)*100:.1f}%"
        )

    console.print(table)
    console.print(f"\n[bold]Total keywords tracked: {len(rows)}[/bold]")
