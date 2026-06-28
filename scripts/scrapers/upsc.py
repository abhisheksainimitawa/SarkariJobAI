import httpx
import hashlib
from selectolax.parser import HTMLParser
from .base import BaseScraper, RawJobDict

BASE_URL = "https://upsc.gov.in/whatsnew"


class UPSCScraper(BaseScraper):
    source_name = "upsc"

    def fetch_listings(self) -> list[RawJobDict]:
        try:
            resp = httpx.get(BASE_URL, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as e:
            print(f"[UPSC] fetch failed: {e}")
            return []

        tree = HTMLParser(resp.text)
        results = []
        # UPSC "What's New" page: notifications are in table rows or list items
        # with links to PDFs or notification pages — filter by URL pattern
        JOB_KEYWORDS = ("exam", "recruit", "vacanc", "notif", "advt", "post",
                        "applic", "select", "appoint", ".pdf")
        NAV_SKIP = ("home", "about", "contact", "sitemap", "faq", "tender",
                    "annual report", "right to information", "constitution",
                    "secretariat", "historical", "provisions", "commission")

        for a in tree.css("a[href]"):
            text = a.text(strip=True)
            if not text or len(text) < 15:
                continue
            text_lower = text.lower()
            if any(skip in text_lower for skip in NAV_SKIP):
                continue
            href = a.attributes.get("href", "")
            href_lower = href.lower()
            if not any(kw in text_lower or kw in href_lower for kw in JOB_KEYWORDS):
                continue
            if not href.startswith("http"):
                href = "https://upsc.gov.in" + href
            job_id = hashlib.sha256(href.encode()).hexdigest()[:16]
            results.append(RawJobDict(
                source_name=self.source_name,
                source_job_id=job_id,
                title=text[:200],
                organization="Union Public Service Commission",
                raw_text=text,
                apply_url=href,
            ))
        return results[:30]
