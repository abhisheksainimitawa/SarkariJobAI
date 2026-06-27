from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawJobDict:
    source_name: str
    source_job_id: str
    title: str
    organization: str
    raw_text: str
    apply_url: str = ""
    deadline_str: str = ""
    extra: dict = field(default_factory=dict)


class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    def fetch_listings(self) -> list[RawJobDict]:
        ...
