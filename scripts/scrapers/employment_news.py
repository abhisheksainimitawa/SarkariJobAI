import feedparser
import hashlib
from .base import BaseScraper, RawJobDict

RSS_URL = "https://www.employmentnews.gov.in/New/rss.aspx"


class EmploymentNewsScraper(BaseScraper):
    source_name = "employment_news"

    def fetch_listings(self) -> list[RawJobDict]:
        feed = feedparser.parse(RSS_URL)
        results = []
        for entry in feed.entries:
            raw = f"{entry.get('title', '')}\n{entry.get('summary', '')}"
            job_id = hashlib.sha256(entry.get("link", raw).encode()).hexdigest()[:16]
            results.append(RawJobDict(
                source_name=self.source_name,
                source_job_id=job_id,
                title=entry.get("title", "Unknown"),
                organization="Employment News",
                raw_text=raw,
                apply_url=entry.get("link", ""),
            ))
        return results
