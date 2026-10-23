"""
Data models for the Nagpur Hackathon Monitor.
Defines the core HackathonEvent schema and formatting helpers.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class HackathonEvent:
    id: str                                  # e.g. "unstop:1346649" or "devfolio:hacknagpur"
    source: str                              # "Unstop", "Devfolio", or "Devpost"
    title: str
    url: str
    description: str = ""
    organizer: str = "TBA"
    venue: str = "TBA"
    mode: str = "Online"                     # "In-Person", "Online", or "Hybrid"
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    registration_deadline: Optional[str] = None
    min_team_size: int = 1
    max_team_size: Optional[int] = None
    solo_allowed: bool = True
    eligibility: str = "Open to all"
    prize_pool: str = "Not disclosed"
    tracks: List[str] = field(default_factory=list)
    score: int = 0
    matched_reasons: List[str] = field(default_factory=list)
    is_nagpur_local: bool = False
    is_maharashtra: bool = False
    is_active: bool = True
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HackathonEvent":
        """Reconstruct HackathonEvent from dictionary, ignoring excess keys."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @property
    def solo_badge(self) -> str:
        """Markdown badge for solo participation eligibility."""
        if self.solo_allowed:
            return "🟢 Solo Eligible (1 Member)"
        return f"👥 Teams Only ({self.min_team_size}-{self.max_team_size or 'N'} members)"

    @property
    def location_badge(self) -> str:
        """Markdown badge for location/venue."""
        if self.is_nagpur_local:
            return f"📍 **Nagpur / Vidarbha Local** ({self.venue or 'Nagpur'})"
        elif self.is_maharashtra:
            return f"🏢 Maharashtra ({self.city or self.venue or 'MH'})"
        elif self.mode.lower() in ("online", "virtual"):
            return "🌐 Online / Virtual"
        elif self.mode.lower() == "hybrid":
            return f"🔄 Hybrid ({self.venue or 'Online + On-site'})"
        return f"🏢 In-Person ({self.venue or 'On-site'})"

    def summary_markdown(self) -> str:
        """Generate formatted Markdown card for GitHub issues or chat alerts."""
        tracks_str = ", ".join(f"`{t}`" for t in self.tracks) if self.tracks else "General / Open Innovation"
        reasons_list = "\n".join(f"- {r}" for r in self.matched_reasons) or "- Standard Discovery"

        return f"""### [{self.title}]({self.url})
**Source:** {self.source} | **Score:** `{self.score}/100` | **Mode:** {self.mode}

- **📍 Venue:** {self.venue or 'Online'}
- **👤 Participation:** {self.solo_badge}
- **⏰ Registration Deadline:** {self.registration_deadline or 'Check link'}
- **📅 Event Dates:** {self.start_date or 'TBA'} - {self.end_date or 'TBA'}
- **🏆 Prize Pool:** {self.prize_pool}
- **🏷️ Tracks:** {tracks_str}
- **🏢 Organizer:** {self.organizer}
- **🎓 Eligibility:** {self.eligibility[:200] + ('...' if len(self.eligibility) > 200 else '')}

#### 🎯 Priority Match Factors:
{reasons_list}

👉 **[Register Now on {self.source}]({self.url})**
"""
