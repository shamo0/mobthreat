import argparse
import logging
import time
import sys
import json
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init

from .config import load_config
from .scanner.playstore import PlayStoreScanner
from .scanner.appstore import AppStoreScanner
from .detector import compare_apps, is_suspicious
from .notifier import Notifier

init(autoreset=True)


def setup_logging(level: str):
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout
    )


def print_config_summary(config):
    """Show loaded threshold and scan configuration."""
    t = config.thresholds
    get = (lambda k, d=None: t.get(k, d)) if isinstance(t, dict) else (lambda k, d=None: getattr(t, k, d))
    print(f"{Fore.CYAN}{Style.BRIGHT}\n[CONFIG SUMMARY]{Style.RESET_ALL}")
    print(
        f"  • Name fuzzy threshold : {get('name_fuzzy')}\n"
        f"  • Overall score         : {get('overall_score')}\n"
        f"  • Package exact match   : {get('package_exact')}\n"
        f"  • Icon pHash distance   : {get('icon_phash_distance')}\n"
        f"  • Description weight    : {get('description_weight')}\n"
        f"  • Description bonus     : {get('description_bonus')}"
    )
    print(f"  • Poll interval (mins)  : {config.poll_interval_minutes}")
    print(f"  • Notifications         : Slack={config.notifications.slack_webhook}, Discord={config.notifications.discord_webhook}\n")


def scan_target(target, config, quiet=False):
    scanners = {"android": PlayStoreScanner(), "ios": AppStoreScanner()}
    notifier = Notifier(config.notifications.slack_webhook, config.notifications.discord_webhook)
    findings = []
    notified_ids = set()
    cache_file = f".cache_{target.id}.json"
    seen_packages = set()
    start_time = time.time()

    print(f"\n{Fore.CYAN}{Style.BRIGHT}→ Scanning target: {target.company_name}{Style.RESET_ALL}")
    print(f"  Keywords: {', '.join(target.keywords)}")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                seen_packages = set(json.load(f))
            if not quiet:
                print(f"  {Fore.BLUE}Loaded {len(seen_packages)} cached packages{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Failed to load cache: {e}")
            seen_packages = set()

    total_scanned = 0
    tasks = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for keyword in target.keywords:
            for platform, scanner in scanners.items():
                tasks.append(executor.submit(scanner.fetch_by_keyword, keyword))

        for future in as_completed(tasks):
            try:
                results = future.result(timeout=25)
            except Exception as e:
                logging.getLogger("mobthreat").warning("Scanner error: %s", e)
                continue

            if not results:
                continue

            platform = results[0].platform if results else "unknown"
            keyword = getattr(results[0], "keyword", None) or "unknown"
            total_scanned += len(results)
            if not quiet:
                print(f"  {Fore.MAGENTA}{platform.upper():<8}{Style.RESET_ALL} → {len(results)} apps for keyword '{keyword}'")

            for cand in results:
                if cand.package in seen_packages:
                    continue
                for known in target.known_apps:
                    if known.platform != platform:
                        continue
                    match = compare_apps(known.name, known.package or known.bundle, cand, config.thresholds)
                    if is_suspicious(match, config.thresholds):
                        app_id = match.candidate.package or match.candidate.title
                        if app_id in notified_ids:
                            continue
                        notified_ids.add(app_id)
                        findings.append((known, match))

    duration = time.time() - start_time
    print(f"\n  {Fore.BLUE}[SUMMARY]{Style.RESET_ALL} Scanned {total_scanned} apps in {duration:.1f}s")

    if not findings:
        print(f"  {Fore.GREEN}[✓]{Style.RESET_ALL} No impersonations for {target.company_name}\n")
    else:
        print(f"  {Fore.RED}{Style.BRIGHT}[⚠] {len(findings)} potential impersonations detected!{Style.RESET_ALL}\n")
        exported = []
        for known, match in findings:
            title = f"{match.candidate.title} ({match.candidate.platform})"
            body = (
                f"Target: {target.company_name}\n"
                f"Known app: {known.name} ({known.package or known.bundle})\n"
                f"Candidate: {match.candidate.title}\n"
                f"Package/bundle: {match.candidate.package}\n"
                f"Developer: {match.candidate.developer}\n"
                f"Name score: {match.name_score:.1f}\n"
                f"Overall score: {match.overall_score:.1f}\n"
                f"Store link: {match.candidate.raw.get('url') or 'N/A'}\n"
                f"Icon: {match.candidate.icon_url}\n"
            )

            if not quiet:
                print(f"{Fore.YELLOW}• {title}{Style.RESET_ALL}")
                print(f"    Developer     : {match.candidate.developer}")
                print(f"    Package/Bundle: {match.candidate.package}")
                print(f"    Name Score    : {match.name_score:.1f}")
                print(f"    Overall Score : {match.overall_score:.1f}")
                print(f"    Store Link    : {match.candidate.raw.get('url') or 'N/A'}")
                print(f"    Icon          : {match.candidate.icon_url}\n")

            notifier.notify(f"Possible impersonation: {title}", body)
            exported.append({
                "candidate": match.candidate.title,
                "platform": match.candidate.platform,
                "developer": match.candidate.developer,
                "package": match.candidate.package,
                "store_link": match.candidate.raw.get("url"),
                "icon": match.candidate.icon_url,
                "name_score": match.name_score,
                "overall_score": match.overall_score,
            })

        out_file = f"findings_{target.id}.json"
        with open(out_file, "w") as f:
            json.dump(exported, f, indent=2)
        print(f"  {Fore.CYAN}[EXPORTED]{Style.RESET_ALL} {len(exported)} findings → {out_file}")

    try:
        all_packages = seen_packages.union({
            match.candidate.package for _, match in findings if match.candidate.package
        })
        with open(cache_file, "w") as f:
            json.dump(list(all_packages), f, indent=2)
        if not quiet:
            print(f"  {Fore.BLUE}[CACHE]{Style.RESET_ALL} Updated ({len(all_packages)} entries)\n")
    except Exception as e:
        logging.getLogger("mobthreat").warning("Failed to write cache: %s", e)


def run_loop(config_path: str, quiet=False):
    config = load_config(config_path)
    setup_logging(config.logging.get("level", "INFO"))
    print_config_summary(config)
    poll = config.poll_interval_minutes * 60
    logger = logging.getLogger("mobthreat")
    logger.info("Starting monitor (interval %d minutes)", config.poll_interval_minutes)

    while True:
        for t in config.targets:
            try:
                scan_target(t, config, quiet=quiet)
            except Exception as e:
                logger.exception("Error scanning target %s: %s", t.id, e)
        logger.info("Scan pass complete; sleeping %d seconds", poll)
        time.sleep(poll)


def main():
    parser = argparse.ArgumentParser(description="mobthreat: mobile app lookalike monitor")
    parser.add_argument("--config", "-c", default="config.yml", help="Path to config.yml")
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.logging.get("level", "INFO"))
    print_config_summary(config)

    if args.once:
        for t in config.targets:
            scan_target(t, config, quiet=args.quiet)
    else:
        run_loop(args.config, quiet=args.quiet)


if __name__ == "__main__":
    main()
