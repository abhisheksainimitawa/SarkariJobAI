import httpx
import hashlib
from selectolax.parser import HTMLParser
from .base import BaseScraper, RawJobDict

BASE_URL = "https://ssc.nic.in/Portal/LatestNotices"


class SSCScraper(BaseScraper):
    source_name = "ssc"

    def fetch_listings(self) -> list[RawJobDict]:
        try:
            resp = httpx.get(BASE_URL, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as e:
            print(f"[SSC] fetch failed: {e}")
            return []

        tree = HTMLParser(resp.text)
        results = []
        for a in tree.css("a[href]"):
            text = a.text(strip=True)
            if not text or len(text) < 10:
                continue
            href = a.attributes.get("href", "")
            if not href.startswith("http"):
                href = "https://ssc.nic.in" + href
            job_id = hashlib.sha256(href.encode()).hexdigest()[:16]
            results.append(RawJobDict(
                source_name=self.source_name,
                source_job_id=job_id,
                title=text[:200],
                organization="Staff Selection Commission",
                raw_text=text,
                apply_url=href,
            ))
        return results[:30]
