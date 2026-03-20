"""WordPress REST API client."""
import requests
from requests.auth import HTTPBasicAuth
from config import WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD


class WPClient:
    def __init__(self, site_url=None, username=None, app_password=None):
        self.base = (site_url or WP_SITE_URL).rstrip("/")
        self.auth = HTTPBasicAuth(
            username or WP_USERNAME,
            app_password or WP_APP_PASSWORD
        )
        self.api = f"{self.base}/wp-json/wp/v2"

    def _get(self, endpoint, params=None):
        r = requests.get(f"{self.api}{endpoint}", auth=self.auth, params=params or {})
        r.raise_for_status()
        return r.json()

    def _patch(self, endpoint, data):
        r = requests.post(
            f"{self.api}{endpoint}",
            auth=self.auth,
            json=data,
            headers={"X-HTTP-Method-Override": "PATCH"}
        )
        r.raise_for_status()
        return r.json()

    def _post(self, endpoint, data):
        r = requests.post(f"{self.api}{endpoint}", auth=self.auth, json=data)
        r.raise_for_status()
        return r.json()

    def get_posts(self, per_page=100, page=1, post_type="posts"):
        return self._get(f"/{post_type}", {"per_page": per_page, "page": page, "status": "publish"})

    def get_pages(self, per_page=100):
        return self._get("/pages", {"per_page": per_page, "status": "publish"})

    def get_all_posts(self):
        all_posts = []
        for post_type in ["posts", "pages"]:
            page = 1
            while True:
                batch = self.get_posts(per_page=100, page=page, post_type=post_type)
                if not batch:
                    break
                all_posts.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return all_posts

    def update_post(self, post_id, data):
        return self._patch(f"/posts/{post_id}", data)

    def update_page(self, page_id, data):
        return self._patch(f"/pages/{page_id}", data)

    def create_post(self, title, content, status="publish", meta=None):
        data = {"title": title, "content": content, "status": status}
        if meta:
            data["meta"] = meta
        return self._post("/posts", data)

    def get_media(self, per_page=100):
        return self._get("/media", {"per_page": per_page, "media_type": "image"})
