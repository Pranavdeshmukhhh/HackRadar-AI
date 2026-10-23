"""
Scoring and prioritization engine for hackathons.
Applies weighted boosts for Nagpur regional venues, Maharashtra proximity,
Solo participation eligibility, and AI/Software tracks.
"""

import re
import logging
from typing import List, Dict, Any, Tuple
from .models import HackathonEvent

logger = logging.getLogger(__name__)


class HackathonMatcher:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        scoring_cfg = config.get("scoring", {})
        self.weights = scoring_cfg.get("weights", {
            "nagpur_regional_boost": 45,
            "maharashtra_regional_boost": 25,
            "online_hybrid_boost": 15,
            "solo_boost": 35,
            "track_match_boost": 25,
        })
        self.min_qualifying_score = scoring_cfg.get("min_qualifying_score", 40)

        keywords_cfg = config.get("keywords", {})
        self.nagpur_keywords = [k.lower().strip() for k in keywords_cfg.get("nagpur_regional", [])]
        self.maharashtra_keywords = [k.lower().strip() for k in keywords_cfg.get("maharashtra_regional", [])]
        self.track_keywords = [k.lower().strip() for k in keywords_cfg.get("tracks", [])]

    def _contains_keyword(self, text: str, keywords: List[str]) -> Tuple[bool, List[str]]:
        """Check if any keyword is present in text using boundary-aware matching."""
        if not text:
            return False, []
        text_lower = text.lower()
        matched = []
        for kw in keywords:
            # Match phrases or words with word boundary
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if re.search(pattern, text_lower):
                matched.append(kw)
        return len(matched) > 0, matched

    def score_event(self, event: HackathonEvent) -> HackathonEvent:
        """
        Evaluate and score a single hackathon event based on:
        - Nagpur/Vidarbha regional venue (+45 pts)
        - Maharashtra regional venue (+25 pts)
        - Online / Hybrid accessibility (+15 pts)
        - Solo participation allowed (+35 pts)
        - AI / Software Development track match (+25 pts)
        """
        score = 0
        reasons: List[str] = []

        # Aggregate searchable text blocks
        location_text = f"{event.venue or ''} {event.city or ''} {event.state or ''}"
        full_text = f"{event.title} {event.description} {event.organizer} {location_text}"

        # 1. Nagpur / Vidarbha Regional Boost (+45 pts)
        is_nagpur, nagpur_matches = self._contains_keyword(location_text, self.nagpur_keywords)
        if not is_nagpur:
            # Also check organizer or title (e.g. "VNIT Nagpur Hackathon")
            is_nagpur, nagpur_matches = self._contains_keyword(f"{event.organizer} {event.title}", self.nagpur_keywords)

        if is_nagpur:
            boost = self.weights.get("nagpur_regional_boost", 45)
            score += boost
            event.is_nagpur_local = True
            reasons.append(f"📍 **Nagpur / Vidarbha Local Match** (+{boost} pts) [{', '.join(nagpur_matches[:2]).title()}]")

        # 2. Maharashtra Regional Boost (+25 pts) - if not already Nagpur
        elif not is_nagpur:
            is_mh, mh_matches = self._contains_keyword(location_text, self.maharashtra_keywords)
            if not is_mh:
                is_mh, mh_matches = self._contains_keyword(f"{event.organizer} {event.title}", self.maharashtra_keywords)

            if is_mh:
                boost = self.weights.get("maharashtra_regional_boost", 25)
                score += boost
                event.is_maharashtra = True
                reasons.append(f"🏢 **Maharashtra Proximity** (+{boost} pts) [{', '.join(mh_matches[:2]).title()}]")

        # 3. Online / Hybrid Accessibility (+15 pts)
        mode_lower = event.mode.lower()
        if mode_lower in ("online", "virtual", "hybrid") or "online" in location_text.lower() or "hybrid" in location_text.lower():
            boost = self.weights.get("online_hybrid_boost", 15)
            score += boost
            reasons.append(f"🌐 **Accessible {event.mode} Mode** (+{boost} pts)")

        # 4. Solo Participation Boost (+35 pts)
        if event.solo_allowed:
            boost = self.weights.get("solo_boost", 35)
            score += boost
            reasons.append(f"👤 **Solo Eligible (1 Member)** (+{boost} pts)")

        # 5. Track Match (+25 pts)
        tracks_text = " ".join(event.tracks) if event.tracks else ""
        has_track, track_matches = self._contains_keyword(f"{tracks_text} {event.title} {event.description}", self.track_keywords)
        if has_track:
            boost = self.weights.get("track_match_boost", 25)
            score += boost
            top_tracks = [t.upper() if len(t) <= 4 else t.title() for t in track_matches[:3]]
            reasons.append(f"🤖 **AI & Software Tracks** (+{boost} pts) [{', '.join(top_tracks)}]")

        # Attach computed score and reasons
        event.score = score
        event.matched_reasons = reasons
        return event

    def filter_and_rank(
        self,
        events: List[HackathonEvent],
        min_score: int = None,
        solo_only: bool = False
    ) -> List[HackathonEvent]:
        """
        Score, filter by score and solo constraints, and rank events.
        Rank priority:
        1. Nagpur local events first
        2. Score descending
        3. Registration deadline ascending
        """
        threshold = min_score if min_score is not None else self.min_qualifying_score
        processed: List[HackathonEvent] = []

        exclude_finished = self.config.get("filters", {}).get("exclude_finished", False)

        for ev in events:
            # Exclude finished hackathons if configured
            if exclude_finished and not ev.is_active:
                continue

            scored_ev = self.score_event(ev)

            # Filter by solo eligibility if requested
            if solo_only and not scored_ev.solo_allowed:
                continue

            # Filter by qualifying score
            if scored_ev.score >= threshold:
                processed.append(scored_ev)

        # Multi-factor sorting: (Active first, Nagpur Local first, highest score, then deadline)
        def sort_key(e: HackathonEvent):
            active_weight = 1 if e.is_active else 0
            nagpur_weight = 1 if e.is_nagpur_local else 0
            deadline_str = e.registration_deadline or "9999-99-99"
            return (-active_weight, -nagpur_weight, -e.score, deadline_str)

        ranked = sorted(processed, key=sort_key)
        logger.info(f"Filtered {len(events)} down to {len(ranked)} qualified events (min_score={threshold}, solo_only={solo_only})")
        return ranked
