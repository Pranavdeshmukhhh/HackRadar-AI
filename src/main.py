"""
CLI orchestrator for Nagpur Hackathon Monitor.
Supports 24/7 continuous daemon loop (--loop / --daemon), --dry-run, --solo-only,
--update-dashboard, and custom score thresholds.
"""

from __future__ import annotations

import os
import sys
import time
import json
import yaml
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List

from .models import HackathonEvent
from .scrapers import MultiSourceScraper
from .matcher import HackathonMatcher
from .notifier import NotificationManager

# Setup clean, informative logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hackathon-monitor")

# Safe encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file, with fallback defaults."""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    logger.warning(f"Config file '{config_path}' not found, using internal defaults.")
    return {}


def load_seen_state(seen_file: str) -> Dict[str, Any]:
    """Load seen hackathon records to prevent duplicate notifications."""
    if os.path.exists(seen_file):
        try:
            with open(seen_file, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            logger.error(f"Error loading {seen_file}, starting fresh: {e}")
            return {}
    return {}


def save_seen_state(seen_file: str, seen_data: Dict[str, Any]) -> None:
    """Save updated seen hackathon records."""
    os.makedirs(os.path.dirname(os.path.abspath(seen_file)), exist_ok=True)
    with open(seen_file, "w", encoding="utf-8") as f:
        json.dump(seen_data, f, indent=2, ensure_ascii=False)


def print_terminal_summary(events: List[HackathonEvent], new_events: List[HackathonEvent], dry_run: bool) -> None:
    """Print an attractive summary table to stdout."""
    print("\n" + "=" * 80)
    print(" 🚀 NAGPUR AI & SOFTWARE HACKATHON MONITOR SUMMARY")
    print("=" * 80)
    print(f" Total Qualified Hackathons: {len(events)}")
    print(f" New / Unseen Hackathons:    {len(new_events)} {'[DRY RUN]' if dry_run else ''}")
    print("-" * 80)
    print(f"{'SCORE':<7} | {'SOURCE':<9} | {'MODE':<10} | {'SOLO?':<8} | {'TITLE'}")
    print("-" * 80)

    for e in events[:30]:  # Print top 30 to keep console readable
        solo_str = "Solo ✅" if e.solo_allowed else "Team 👥"
        is_new_mark = "⭐ NEW " if e in new_events else "       "
        title_snip = e.title if len(e.title) <= 38 else e.title[:35] + "..."
        local_flag = "📍" if e.is_nagpur_local else "  "
        print(f"{e.score:>3}/100 {local_flag}| {e.source:<9} | {e.mode:<10} | {solo_str:<8} | {is_new_mark}{title_snip}")

    if len(events) > 30:
        print(f"... and {len(events) - 30} more qualified hackathons (see HACKATHONS.md)")

    print("=" * 80 + "\n")


def run_monitor_cycle(args, config: Dict[str, Any], seen_data: Dict[str, Any], seen_file: str) -> int:
    """Execute one complete scraping, scoring, alerting, and dashboard cycle."""
    logger.info("Initializing multi-source hackathon scrapers...")
    scraper = MultiSourceScraper(config)
    raw_events = scraper.scrape_all()

    # 2. Match and score hackathons
    logger.info("Evaluating hackathon scores with Nagpur + Solo prioritization engine...")
    matcher = HackathonMatcher(config)
    qualified_events = matcher.filter_and_rank(
        raw_events,
        min_score=args.min_score,
        solo_only=args.solo_only,
    )

    # 3. Identify new events
    new_events: List[HackathonEvent] = []
    for ev in qualified_events:
        if ev.id not in seen_data or args.force_notify:
            new_events.append(ev)

    # 4. Print CLI summary
    print_terminal_summary(qualified_events, new_events, args.dry_run)

    # 5. Alert dispatch
    notif_mgr = NotificationManager(config)
    if new_events:
        logger.info(f"Dispatching alerts for {len(new_events)} new hackathons...")
        results = notif_mgr.dispatch_all(new_events, is_dry_run=args.dry_run)
        logger.info(f"Alert dispatch results: {results}")

        if not args.dry_run:
            now_iso = datetime.now(timezone.utc).isoformat()
            for ev in new_events:
                seen_data[ev.id] = {
                    "title": ev.title,
                    "url": ev.url,
                    "score": ev.score,
                    "source": ev.source,
                    "last_notified": now_iso,
                    "is_nagpur_local": ev.is_nagpur_local,
                    "solo_allowed": ev.solo_allowed,
                }
            save_seen_state(seen_file, seen_data)
            logger.info(f"Updated persistent seen cache ({len(seen_data)} total recorded)")
    else:
        logger.info("No new hackathons to alert in this cycle.")

    # 6. Update Dashboard
    if args.update_dashboard or config.get("notifiers", {}).get("dashboard", {}).get("enabled", True):
        logger.info("Updating live repository dashboard HACKATHONS.md...")
        notif_mgr.update_dashboard(qualified_events)

        logger.info("Generating interactive web app in docs/ for GitHub Pages...")
        try:
            from .web_generator import generate_web_dashboard
            web_path = generate_web_dashboard(qualified_events, output_dir="docs")
            logger.info(f"Interactive web dashboard generated at {web_path}")
        except Exception as e:
            logger.error(f"Error generating web dashboard: {e}", exc_info=True)

    logger.info("Hackathon monitoring cycle completed successfully.")
    return len(new_events)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nagpur Hackathon Monitor: 24/7 Discovery, Scoring, and Multi-Channel Alerts"
    )
    parser.add_argument(
        "--loop",
        "--daemon",
        action="store_true",
        help="Run continuously in 24/7 daemon loop mode",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Interval in minutes between scrapings in 24/7 daemon mode (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without sending alerts or mutating seen history",
    )
    parser.add_argument(
        "--solo-only",
        action="store_true",
        help="Filter strictly for hackathons permitting solo participants (1 member)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle and exit immediately (default in CI/GitHub Actions)",
    )
    parser.add_argument(
        "--update-dashboard",
        action="store_true",
        help="Force regeneration of HACKATHONS.md live dashboard",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Override minimum qualifying score threshold (e.g. --min-score 50)",
    )
    parser.add_argument(
        "--force-notify",
        action="store_true",
        help="Ignore seen history and notify all matching hackathons",
    )
    parser.add_argument(
        "--include-finished",
        action="store_true",
        help="Include finished/past hackathons in addition to active open ones",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )

    args = parser.parse_args()

    # 1. Load configuration
    config = load_config(args.config)
    if args.include_finished:
        config.setdefault("filters", {})["exclude_finished"] = False
    seen_file = config.get("storage", {}).get("seen_file", "data/seen_hackathons.json")
    seen_data = load_seen_state(seen_file)

    is_ci = bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))
    is_daemon = (args.loop or config.get("scheduler", {}).get("enabled", False)) and not (args.once or is_ci)
    interval_minutes = args.interval or config.get("scheduler", {}).get("interval_minutes", 60)

    if not is_daemon:
        run_monitor_cycle(args, config, seen_data, seen_file)
        return 0

    logger.info("=" * 75)
    logger.info(" 🚀 NAGPUR HACKATHON MONITOR — 24/7 CONTINUOUS DAEMON MODE ACTIVE")
    logger.info(f" ⏱️ Scraping Cycle Interval: Every {interval_minutes} minutes ({interval_minutes * 60} seconds)")
    logger.info(" 📡 Sources: Unstop, Devfolio, Devpost, HackerEarth, MLH, College Portals")
    logger.info(" 🛑 Press Ctrl+C at any time to gracefully terminate.")
    logger.info("=" * 75)

    cycle_count = 0
    while True:
        cycle_count += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n>>> Starting Scraping Cycle #{cycle_count} at {now_str} <<<")
        try:
            seen_data = load_seen_state(seen_file)
            run_monitor_cycle(args, config, seen_data, seen_file)
        except Exception as e:
            logger.error(f"Error occurred in cycle #{cycle_count}: {e}", exc_info=True)

        logger.info(f"<<< Cycle #{cycle_count} complete. Waiting {interval_minutes} minutes for next 24/7 scan... >>>")
        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("\n24/7 Daemon stopped by user. Goodbye!")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
