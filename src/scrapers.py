"""
Multi-source connectors for Unstop, Devfolio, Devpost, HackerEarth, MLH, and Crawl4AI.
Extracts event details, dates, venues, solo policies, tracks, prize pools, and college affiliations.
High-throughput discovery with Crawl4AI browser crawling and native fallback.
"""

from __future__ import annotations

import re
import sys
import socket
import logging
import time
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit

import requests
try:
    import urllib3.util.connection as urllib3_cn
except ImportError:
    import requests.packages.urllib3.util.connection as urllib3_cn

from .models import HackathonEvent

# Configure logging
logger = logging.getLogger(__name__)

# Force IPv4 socket resolution only on Windows to prevent dual-stack resets
if sys.platform == "win32":
    try:
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
    except Exception:
        pass

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_html(raw_html: Optional[str]) -> str:
    """Strip HTML tags and clean whitespace."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(raw_html))
    return re.sub(r"\s+", " ", clean).strip()


class BaseScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def scrape(self) -> List[HackathonEvent]:
        raise NotImplementedError


# =====================================================================
# 1. UNSTOP CONNECTOR (High-Volume Indian University & College Portal)
# =====================================================================
class UnstopScraper(BaseScraper):
    """
    High-volume connector for Unstop (formerly Dare2Compete).
    Indexes 1,000+ opportunities across hundreds of Indian colleges and universities.
    Uses respectful throttling between pages to avoid anti-bot connection resets.
    """
    SEARCH_URL = "https://unstop.com/api/public/opportunity/search-result"

    def scrape(self, pages: int = 4, per_page: int = 50) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        try:
            for page in range(1, pages + 1):
                params = {
                    "opportunity": "hackathons",
                    "per_page": per_page,
                    "page": page,
                }
                resp = self.session.get(self.SEARCH_URL, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(f"Unstop API page {page} returned HTTP {resp.status_code}")
                    break

                payload = resp.json()
                data_block = payload.get("data", {})
                items = data_block.get("data", []) if isinstance(data_block, dict) else []
                if not items:
                    break

                for item in items:
                    raw_id = item.get("id")
                    if not raw_id:
                        continue

                    event_id = f"unstop:{raw_id}"
                    title = item.get("title") or "Unstop Hackathon"
                    public_url = item.get("public_url", "")
                    url = f"https://unstop.com/{public_url}" if public_url else "https://unstop.com/hackathons"

                    org_info = item.get("organisation", {})
                    org_name = org_info.get("name") if isinstance(org_info, dict) else "Unstop Host"

                    reqs = item.get("regnRequirements", {}) or {}
                    try:
                        min_team_size = int(reqs.get("min_team_size") or 1)
                    except (ValueError, TypeError):
                        min_team_size = 1

                    try:
                        max_team_size = int(reqs.get("max_team_size") or 1)
                    except (ValueError, TypeError):
                        max_team_size = None

                    solo_allowed = min_team_size <= 1
                    reg_deadline = reqs.get("end_regn_dt")

                    reg_status = str(reqs.get("reg_status", "")).upper()
                    remain_days = str(reqs.get("remain_days", "")).lower()
                    is_active = not (reg_status == "FINISHED" or remain_days == "ended")

                    # Location & Mode
                    region = item.get("region")
                    city = item.get("city")
                    loc_type = reqs.get("work_location_type", "")
                    if loc_type == "online" or region == "online":
                        mode = "Online"
                        venue = "Online"
                    elif loc_type == "hybrid":
                        mode = "Hybrid"
                        venue = f"{city or region or 'Hybrid'}"
                    else:
                        mode = "In-Person"
                        venue = f"{city or ''} {region or ''}".strip() or (org_name if org_name else "On-Campus / On-Site")

                    tracks: List[str] = []
                    for f in item.get("filters", []) or []:
                        if isinstance(f, dict) and f.get("name"):
                            tracks.append(f["name"])

                    eligibility = reqs.get("eligibility") or "Open to college students & coders"
                    if isinstance(eligibility, str) and eligibility.startswith("{"):
                        eligibility = "Undergraduate / Postgraduate & Engineering students"

                    events.append(
                        HackathonEvent(
                            id=event_id,
                            source="Unstop",
                            title=title,
                            url=url,
                            description=clean_html(item.get("details") or ""),
                            organizer=org_name,
                            venue=venue,
                            mode=mode,
                            city=city,
                            state=region,
                            start_date=reqs.get("start_regn_dt"),
                            end_date=item.get("end_date"),
                            registration_deadline=reg_deadline,
                            min_team_size=min_team_size,
                            max_team_size=max_team_size,
                            solo_allowed=solo_allowed,
                            eligibility=eligibility,
                            prize_pool="Prizes & Certificates",
                            tracks=tracks,
                            is_active=is_active,
                        )
                    )

                time.sleep(0.3)  # Gentle spacing between pages to prevent rate limits

            logger.info(f"Unstop scraper collected {len(events)} hackathons across {pages} pages")
        except Exception as e:
            logger.error(f"Error scraping Unstop: {e}", exc_info=True)

        return events


# =====================================================================
# 2. DEVFOLIO CONNECTOR (Elasticsearch Offset Pagination)
# =====================================================================
class DevfolioScraper(BaseScraper):
    """Connector for Devfolio public hackathon discovery endpoint with offset pagination."""
    SEARCH_URL = "https://api.devfolio.co/api/search/hackathons"

    def scrape(self, max_items: int = 50, chunk_size: int = 25) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        offset = 0

        while offset < max_items:
            chunk = min(chunk_size, max_items - offset)
            payload = {
                "filter": "all",
                "q": "",
                "from": offset,
                "size": chunk,
            }
            try:
                resp = self.session.post(self.SEARCH_URL, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    break

                data = resp.json()
                hits = data.get("hits", {})
                hit_list = hits.get("hits", []) if isinstance(hits, dict) else []
                if not hit_list:
                    break

                for item in hit_list:
                    src = item.get("_source", {})
                    slug = src.get("slug")
                    if not slug:
                        continue

                    name = src.get("name") or slug
                    uuid = src.get("uuid") or slug
                    event_id = f"devfolio:{uuid}"
                    url = f"https://{slug}.devfolio.co"

                    is_online = src.get("is_online", False)
                    city = src.get("city")
                    state = src.get("state")
                    venue = src.get("location") or (f"{city}, {state}" if city else "Virtual / Online" if is_online else "TBA")
                    mode = "Online" if is_online else "Hybrid" if ("hybrid" in str(venue).lower()) else "In-Person"

                    try:
                        min_team_size = int(src.get("team_min") or 1)
                    except (ValueError, TypeError):
                        min_team_size = 1

                    try:
                        max_team_size = int(src.get("team_size") or 1) if src.get("team_size") is not None else None
                    except (ValueError, TypeError):
                        max_team_size = None

                    solo_allowed = min_team_size <= 1

                    tracks: List[str] = []
                    for theme in src.get("themes", []) or []:
                        if isinstance(theme, dict) and theme.get("name"):
                            tracks.append(theme["name"])
                        elif isinstance(theme, str):
                            tracks.append(theme)
                    for tag in src.get("hashtags", []) or []:
                        if isinstance(tag, str):
                            tracks.append(tag)

                    prize_pool = "Not disclosed"
                    prizes = src.get("prizes")
                    if prizes:
                        if isinstance(prizes, str):
                            prize_pool = prizes
                        elif isinstance(prizes, list) and len(prizes) > 0:
                            first_prize = prizes[0]
                            if isinstance(first_prize, dict):
                                prize_pool = f"{first_prize.get('currency', '₹')} {first_prize.get('amount', '')}".strip()

                    desc = clean_html(src.get("desc") or src.get("tagline") or "")

                    is_active = True
                    ends_at = src.get("ends_at")
                    if ends_at:
                        try:
                            from datetime import datetime, timezone
                            end_dt = datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
                            is_active = end_dt > datetime.now(timezone.utc)
                        except Exception:
                            pass

                    events.append(
                        HackathonEvent(
                            id=event_id,
                            source="Devfolio",
                            title=name,
                            url=url,
                            description=desc,
                            organizer=src.get("hosted_by") or "Devfolio Community",
                            venue=venue,
                            mode=mode,
                            city=city,
                            state=state,
                            start_date=src.get("starts_at"),
                            end_date=src.get("ends_at"),
                            registration_deadline=src.get("starts_at"),
                            min_team_size=min_team_size,
                            max_team_size=max_team_size,
                            solo_allowed=solo_allowed,
                            eligibility="Open to students & developers",
                            prize_pool=prize_pool,
                            tracks=tracks,
                            is_active=is_active,
                        )
                    )

                offset += len(hit_list)
                if len(hit_list) < chunk:
                    break

            except Exception as e:
                logger.warning(f"Devfolio offset {offset} error: {e}")
                break

        logger.info(f"Devfolio scraper collected {len(events)} hackathons")
        return events


# =====================================================================
# 3. DEVPOST CONNECTOR (Multi-page Pagination)
# =====================================================================
class DevpostScraper(BaseScraper):
    """Connector for Devpost public hackathons API with multi-page pagination."""
    API_URL = "https://devpost.com/api/hackathons"

    def scrape(self, max_pages: int = 5) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        try:
            for page in range(1, max_pages + 1):
                resp = self.session.get(f"{self.API_URL}?page={page}", timeout=self.timeout)
                if resp.status_code != 200:
                    break

                data = resp.json()
                hacks = data.get("hackathons", [])
                if not hacks:
                    break

                for h in hacks:
                    raw_id = h.get("id") or h.get("analytics_identifier")
                    if not raw_id:
                        continue

                    event_id = f"devpost:{raw_id}"
                    title = h.get("title") or "Devpost Hackathon"
                    url = h.get("url") or f"https://devpost.com/hackathons/{raw_id}"

                    disp_loc = h.get("displayed_location", {})
                    loc_text = disp_loc.get("location", "Online") if isinstance(disp_loc, dict) else str(disp_loc)
                    mode = "Online" if "online" in loc_text.lower() else "In-Person"

                    prize_amount = clean_html(h.get("prize_amount") or "Not disclosed")

                    tracks = []
                    for theme in h.get("themes", []) or []:
                        if isinstance(theme, dict) and theme.get("name"):
                            tracks.append(theme["name"])
                        elif isinstance(theme, str):
                            tracks.append(theme)

                    open_state = str(h.get("open_state", "")).lower()
                    is_active = open_state in ("open", "upcoming", "")

                    events.append(
                        HackathonEvent(
                            id=event_id,
                            source="Devpost",
                            title=title,
                            url=url,
                            description=f"Devpost hackathon. {h.get('time_left_to_submission', '')}",
                            organizer=h.get("organization_name") or "Devpost Community",
                            venue=loc_text,
                            mode=mode,
                            registration_deadline=h.get("submission_period_dates"),
                            min_team_size=1,
                            max_team_size=None,
                            solo_allowed=True,
                            eligibility="Global Devpost Participants",
                            prize_pool=prize_amount,
                            tracks=tracks,
                            is_active=is_active,
                        )
                    )

            logger.info(f"Devpost scraper collected {len(events)} hackathons across {max_pages} pages")
        except Exception as e:
            logger.error(f"Error scraping Devpost: {e}", exc_info=True)

        return events


# =====================================================================
# 4. HACKEREARTH CONNECTOR
# =====================================================================
class HackerEarthScraper(BaseScraper):
    """Connector for HackerEarth hackathons and challenges."""
    EVENTS_URL = "https://www.hackerearth.com/chrome-extension/events/"

    def scrape(self) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        try:
            resp = self.session.get(self.EVENTS_URL, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"HackerEarth API returned HTTP {resp.status_code}")
                return events

            data = resp.json()
            challenge_list = data.get("response", []) if isinstance(data, dict) else []

            for item in challenge_list:
                title = item.get("title")
                url = item.get("url")
                if not title or not url:
                    continue

                challenge_id = re.sub(r"[^a-zA-Z0-9_-]", "", url.rstrip("/").split("/")[-1])
                event_id = f"hackerearth:{challenge_id}"

                is_college = item.get("college", False)
                status = str(item.get("status", "")).upper()
                is_active = status in ("UPCOMING", "ONGOING", "")

                college_note = " (Campus/College Edition)" if is_college else ""
                desc = clean_html(item.get("description") or f"HackerEarth hackathon{college_note}")

                events.append(
                    HackathonEvent(
                        id=event_id,
                        source="HackerEarth",
                        title=title,
                        url=url,
                        description=desc,
                        organizer="HackerEarth Community",
                        venue="Online",
                        mode="Online",
                        start_date=item.get("date"),
                        end_date=item.get("end_date"),
                        registration_deadline=item.get("end_date") or item.get("date"),
                        min_team_size=1,
                        max_team_size=None,
                        solo_allowed=True,
                        eligibility="College Students & Professional Developers" if is_college else "Open to all coders",
                        prize_pool="Prizes, Hiring & Certificates",
                        tracks=["Software", "AI/ML", "Hiring Challenge"],
                        is_active=is_active,
                    )
                )

            logger.info(f"HackerEarth scraper collected {len(events)} hackathons")
        except Exception as e:
            logger.error(f"Error scraping HackerEarth: {e}", exc_info=True)

        return events


# =====================================================================
# 5. MAJOR LEAGUE HACKING (MLH) CONNECTOR
# =====================================================================
class _MLHInertiaParser(HTMLParser):
    """Extract Inertia JSON data-page attribute from official MLH season calendars."""
    def __init__(self):
        super().__init__()
        self.payload: Optional[Dict[str, Any]] = None
        self.active = False
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = dict(attrs)
        if tag == "script" and attr_dict.get("type") == "application/json" and attr_dict.get("data-page") == "app":
            self.active = True
            self.parts = []
        if "data-page" in attr_dict and attr_dict["data-page"].lstrip().startswith("{"):
            try:
                self.payload = json.loads(attr_dict["data-page"])
            except Exception:
                pass

    def handle_data(self, data: str):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag: str):
        if tag == "script" and self.active:
            self.active = False
            try:
                self.payload = json.loads("".join(self.parts))
            except Exception:
                pass


class MLHScraper(BaseScraper):
    """Connector for Major League Hacking (MLH) student calendars."""
    BASE_URL = "https://www.mlh.com/seasons"

    def scrape(self, seasons: Optional[List[int]] = None) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        if not seasons:
            seasons = [2025]

        for season in seasons:
            url = f"{self.BASE_URL}/{season}/events"
            try:
                resp = self.session.get(url, timeout=min(self.timeout, 8))
                if resp.status_code != 200:
                    continue

                parser = _MLHInertiaParser()
                parser.feed(resp.text)
                if not parser.payload:
                    continue

                props = parser.payload.get("props", {})
                upcoming = props.get("upcomingEvents", []) or []
                past = props.get("pastEvents", []) or []
                all_mlh = upcoming + (past[:15] if not upcoming else [])

                for ev in all_mlh:
                    name = ev.get("name")
                    ev_path = ev.get("url") or ""
                    if not name:
                        continue

                    event_url = f"https://www.mlh.com{ev_path}" if ev_path.startswith("/") else (ev_path or url)
                    slug = re.sub(r"[^a-zA-Z0-9_-]", "", ev_path.rstrip("/").split("/")[-1]) or name.lower().replace(" ", "-")
                    event_id = f"mlh:{season}:{slug}"

                    loc = ev.get("location") or "Virtual / Online"
                    format_type = str(ev.get("formatType", "")).lower()
                    mode = "Online" if format_type in ("digital", "virtual", "online") else "In-Person"

                    events.append(
                        HackathonEvent(
                            id=event_id,
                            source="MLH",
                            title=name,
                            url=event_url,
                            description=f"Official MLH {season} Season Member Hackathon. Location: {loc}",
                            organizer="Major League Hacking / Student Community",
                            venue=loc,
                            mode=mode,
                            start_date=ev.get("startsAt"),
                            end_date=ev.get("endsAt"),
                            registration_deadline=ev.get("startsAt"),
                            min_team_size=1,
                            max_team_size=4,
                            solo_allowed=True,
                            eligibility="High School, Undergraduate & University Students worldwide",
                            prize_pool="Swag, Hardware Labs, MLH Points & Trophies",
                            tracks=["Student Innovation", "AI/ML", "Web/Mobile"],
                            is_active=ev in upcoming,
                        )
                    )

            except Exception as e:
                logger.warning(f"MLH season {season} skipped: {e}")

        logger.info(f"MLH scraper collected {len(events)} hackathons")
        return events


# =====================================================================
# 6. CRAWL4AI & DEEP COLLEGE HACKATHON CRAWLER (Concurrent Fallback)
# =====================================================================
class CollegeAndCrawl4AIScraper:
    """
    Deep crawler for Indian College Tech Fests, University Hackathons, and Custom URLs.
    Uses Crawl4AI (AsyncWebCrawler with DeepCrawlStrategy) if installed;
    falls back to fast multi-threaded requests + regex/HTML parsing.
    """

    def __init__(self, seed_urls: Optional[List[str]] = None, max_pages: int = 50, timeout: int = 5):
        self.seed_urls = seed_urls or [
            "https://axisvnit.in",
            "https://techfest.org",
            "https://mind-spark.org",
        ]
        self.max_pages = max_pages
        self.timeout = timeout

    def scrape(self) -> List[HackathonEvent]:
        try:
            import crawl4ai
            logger.info("Crawl4AI library detected: executing async browser crawl engine...")
            return asyncio.run(self._crawl4ai_crawl())
        except ImportError:
            logger.info("Crawl4AI not installed; using high-speed native college scraper fallback.")
            return self._native_crawl()

    async def _crawl4ai_crawl(self) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, DeepCrawlStrategy

            config = CrawlerRunConfig(
                deep_crawl_strategy=DeepCrawlStrategy(max_depth=2, max_pages=self.max_pages),
                word_count_threshold=10,
            )

            async with AsyncWebCrawler() as crawler:
                for start_url in self.seed_urls:
                    result = await crawler.arun(url=start_url, config=config)
                    results = result if isinstance(result, list) else [result]

                    for r in results:
                        text = getattr(r, "markdown", "") or getattr(r, "cleaned_html", "")
                        url = getattr(r, "url", start_url)
                        if "hackathon" in text.lower() or "coding competition" in text.lower():
                            event_id = f"crawl4ai:{re.sub(r'[^a-zA-Z0-9]', '', url)[-30:]}"
                            title_match = re.search(r"#+\s*(.+hackathon.+)", text, re.I)
                            title = title_match.group(1).strip() if title_match else f"Hackathon at {urlsplit(url).netloc}"

                            events.append(
                                HackathonEvent(
                                    id=event_id,
                                    source="College/Crawl4AI",
                                    title=title[:80],
                                    url=url,
                                    description=text[:400],
                                    organizer=urlsplit(url).netloc,
                                    venue=urlsplit(url).netloc,
                                    mode="In-Person",
                                    min_team_size=1,
                                    max_team_size=4,
                                    solo_allowed=True,
                                    eligibility="College & University Students",
                                    prize_pool="Prizes & Certificates",
                                    tracks=["Software", "AI", "Open Innovation"],
                                    is_active=True,
                                )
                            )
        except Exception as e:
            logger.error(f"Error during Crawl4AI crawl: {e}", exc_info=True)

        return events

    def _fetch_seed(self, url: str) -> Optional[HackathonEvent]:
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                html = resp.text
                if re.search(r"\bhackathon\b|\bcoding\s+contest\b|\bcompetition\b", html, re.I):
                    domain = urlsplit(url).netloc
                    title_match = re.search(r"<title>(.*?)</title>", html, re.I)
                    title = title_match.group(1).strip() if title_match else f"Hackathon at {domain}"
                    event_id = f"college:{re.sub(r'[^a-zA-Z0-9]', '', domain)}"
                    return HackathonEvent(
                        id=event_id,
                        source="CollegePortal",
                        title=title[:80],
                        url=url,
                        description=f"College hackathon detected at {domain}. Check official portal for rules and registration.",
                        organizer=domain,
                        venue=domain,
                        mode="In-Person",
                        min_team_size=1,
                        max_team_size=4,
                        solo_allowed=True,
                        eligibility="College and Engineering Students",
                        prize_pool="Prizes & Cash Awards",
                        tracks=["Software", "Web Development", "AI/ML"],
                        is_active=True,
                    )
        except Exception:
            pass
        return None

    def _native_crawl(self) -> List[HackathonEvent]:
        events: List[HackathonEvent] = []
        with ThreadPoolExecutor(max_workers=min(len(self.seed_urls), 4)) as executor:
            futures = [executor.submit(self._fetch_seed, u) for u in self.seed_urls]
            for f in as_completed(futures):
                res = f.result()
                if res:
                    events.append(res)
        logger.info(f"College portal crawler collected {len(events)} hackathons")
        return events


# =====================================================================
# 7. MULTI-SOURCE ORCHESTRATOR
# =====================================================================
class MultiSourceScraper:
    """Orchestrates multi-platform hackathon discovery and deduplication across 1,000+ opportunities."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        scrapers_cfg = config.get("scrapers", {})

        # Devfolio config
        self.devfolio_enabled = scrapers_cfg.get("devfolio", {}).get("enabled", True)
        self.devfolio_max = scrapers_cfg.get("devfolio", {}).get("max_items", 50)
        self.devfolio_timeout = scrapers_cfg.get("devfolio", {}).get("timeout_seconds", 8)

        # Devpost config
        self.devpost_enabled = scrapers_cfg.get("devpost", {}).get("enabled", True)
        self.devpost_pages = scrapers_cfg.get("devpost", {}).get("max_pages", 4)
        self.devpost_timeout = scrapers_cfg.get("devpost", {}).get("timeout_seconds", 8)

        # Unstop config (high volume)
        self.unstop_enabled = scrapers_cfg.get("unstop", {}).get("enabled", True)
        self.unstop_pages = scrapers_cfg.get("unstop", {}).get("pages", 3)
        self.unstop_per_page = scrapers_cfg.get("unstop", {}).get("per_page", 50)
        self.unstop_timeout = scrapers_cfg.get("unstop", {}).get("timeout_seconds", 10)

        # HackerEarth config
        self.hackerearth_enabled = scrapers_cfg.get("hackerearth", {}).get("enabled", True)
        self.hackerearth_timeout = scrapers_cfg.get("hackerearth", {}).get("timeout_seconds", 8)

        # MLH config
        self.mlh_enabled = scrapers_cfg.get("mlh", {}).get("enabled", True)
        self.mlh_seasons = scrapers_cfg.get("mlh", {}).get("seasons", [2025])
        self.mlh_timeout = scrapers_cfg.get("mlh", {}).get("timeout_seconds", 6)

        # College / Crawl4AI config
        self.crawl4ai_enabled = scrapers_cfg.get("crawl4ai", {}).get("enabled", True)
        self.crawl4ai_urls = scrapers_cfg.get("crawl4ai", {}).get("seed_urls", None)
        self.crawl4ai_pages = scrapers_cfg.get("crawl4ai", {}).get("max_pages", 50)
        self.crawl4ai_timeout = scrapers_cfg.get("crawl4ai", {}).get("timeout_seconds", 5)

    def scrape_all(self) -> List[HackathonEvent]:
        all_events: List[HackathonEvent] = []
        seen_keys = set()

        def add_event(ev: HackathonEvent):
            norm_url = ev.url.rstrip("/").lower()
            if ev.id not in seen_keys and norm_url not in seen_keys:
                seen_keys.add(ev.id)
                seen_keys.add(norm_url)
                all_events.append(ev)

        # 1. Unstop (High volume Indian universities & colleges)
        if self.unstop_enabled:
            logger.info(f"Executing Unstop scraper ({self.unstop_pages} pages x {self.unstop_per_page} items)...")
            unstop = UnstopScraper(timeout=self.unstop_timeout)
            for ev in unstop.scrape(pages=self.unstop_pages, per_page=self.unstop_per_page):
                add_event(ev)

        # 2. Devfolio
        if self.devfolio_enabled:
            logger.info(f"Executing Devfolio scraper (up to {self.devfolio_max} items)...")
            devfolio = DevfolioScraper(timeout=self.devfolio_timeout)
            for ev in devfolio.scrape(max_items=self.devfolio_max):
                add_event(ev)

        # 3. Devpost
        if self.devpost_enabled:
            logger.info(f"Executing Devpost scraper ({self.devpost_pages} pages)...")
            devpost = DevpostScraper(timeout=self.devpost_timeout)
            for ev in devpost.scrape(max_pages=self.devpost_pages):
                add_event(ev)

        # 4. HackerEarth
        if self.hackerearth_enabled:
            logger.info("Executing HackerEarth scraper...")
            hackerearth = HackerEarthScraper(timeout=self.hackerearth_timeout)
            for ev in hackerearth.scrape():
                add_event(ev)

        # 5. MLH
        if self.mlh_enabled:
            logger.info("Executing MLH scraper...")
            mlh = MLHScraper(timeout=self.mlh_timeout)
            for ev in mlh.scrape(seasons=self.mlh_seasons):
                add_event(ev)

        # 6. Indian College Portals & Crawl4AI
        if self.crawl4ai_enabled:
            logger.info("Executing Indian College & Crawl4AI deep crawler...")
            crawler = CollegeAndCrawl4AIScraper(
                seed_urls=self.crawl4ai_urls,
                max_pages=self.crawl4ai_pages,
                timeout=self.crawl4ai_timeout,
            )
            for ev in crawler.scrape():
                add_event(ev)

        logger.info(f"Total unified hackathons collected across all sources: {len(all_events)}")
        return all_events
