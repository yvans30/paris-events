#!/usr/bin/env python3
"""Fetches tech/finance events in Paris from Eventbrite, Meetup, and Luma."""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# Eventbrite API
# ---------------------------------------------------------------------------

def fetch_eventbrite(date_from, date_to):
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        print("[WARN] EVENTBRITE_TOKEN non defini, Eventbrite ignore.", file=sys.stderr)
        return []

    headers = {"Authorization": f"Bearer {token}"}
    all_events = []

    # Category 102 = Science & Tech, 101 = Business & Finance
    for category in ["102", "101"]:
        params = {
            "location.address": "Paris, France",
            "location.within": "15km",
            "start_date.range_start": f"{date_from}T00:00:00",
            "start_date.range_end": f"{date_to}T23:59:59",
            "categories": category,
            "expand": "venue,ticket_availability",
            "page_size": 50,
        }

        try:
            resp = requests.get(
                "https://www.eventbriteapi.com/v3/events/search/",
                headers=headers, params=params, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] Eventbrite API error (cat {category}): {e}", file=sys.stderr)
            continue

        for ev in data.get("events", []):
            ticket = ev.get("ticket_availability") or {}
            min_price = ticket.get("minimum_ticket_price") or {}
            price_val = float(min_price.get("value", 0) or 0)
            if price_val > 50:
                continue

            venue = ev.get("venue") or {}
            addr = venue.get("address") or {}
            address = ", ".join(filter(None, [addr.get("address_1"), addr.get("city")]))
            dt = ev["start"]["local"]

            all_events.append({
                "title": ev["name"]["text"],
                "date": dt[:10],
                "time": dt[11:16],
                "venue": venue.get("name", ""),
                "address": address,
                "type": "Conference",
                "price": "Gratuit" if price_val == 0 else f"{price_val:.0f} EUR",
                "url": ev["url"],
                "description": (ev.get("description") or {}).get("text", "")[:250],
                "source": "eventbrite",
            })

    return all_events


# ---------------------------------------------------------------------------
# Eventbrite scraping fallback (no API token needed)
# ---------------------------------------------------------------------------

def fetch_eventbrite_scrape(date_from, date_to):
    session = requests.Session()
    session.headers.update(SESSION_HEADERS)

    all_events = []
    urls = [
        "https://www.eventbrite.fr/d/france--paris/tech/",
        "https://www.eventbrite.fr/d/france--paris/finance/",
    ]

    for url in urls:
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Eventbrite uses ItemList JSON-LD with ListItem entries
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Extract event items from ItemList or direct Event objects
                raw_items = []
                if isinstance(data, dict):
                    if data.get("@type") == "ItemList":
                        for li in data.get("itemListElement", []):
                            raw_items.append(li.get("item", li))
                    elif data.get("@type") == "Event":
                        raw_items.append(data)
                elif isinstance(data, list):
                    raw_items.extend(data)

                for item in raw_items:
                    if not isinstance(item, dict):
                        continue

                    start = item.get("startDate", "")
                    event_date = start[:10]
                    if event_date < date_from or event_date > date_to:
                        continue

                    location = item.get("location") or {}
                    loc_addr = location.get("address") or {}
                    raw_offers = item.get("offers") or {}
                    if isinstance(raw_offers, list):
                        offers = raw_offers[0] if raw_offers else {}
                    else:
                        offers = raw_offers
                    price_val = float(offers.get("lowPrice", offers.get("price", 0)) or 0)
                    if price_val > 50:
                        continue

                    all_events.append({
                        "title": item.get("name", ""),
                        "date": event_date,
                        "time": start[11:16] if len(start) > 10 else "",
                        "venue": location.get("name", ""),
                        "address": ", ".join(filter(None, [
                            loc_addr.get("streetAddress"),
                            loc_addr.get("addressLocality"),
                        ])),
                        "type": "Conference",
                        "price": "Gratuit" if price_val == 0 else f"{price_val:.0f} EUR",
                        "url": item.get("url", ""),
                        "description": (item.get("description") or "")[:250],
                        "source": "eventbrite_scrape",
                    })
        except Exception as e:
            print(f"[WARN] Eventbrite scrape error ({url}): {e}", file=sys.stderr)

    return all_events


# ---------------------------------------------------------------------------
# Meetup GraphQL API
# ---------------------------------------------------------------------------

def fetch_meetup(date_from, date_to):
    token = os.environ.get("MEETUP_API_KEY")
    if not token:
        print("[WARN] MEETUP_API_KEY non defini, Meetup ignore.", file=sys.stderr)
        return []

    query = """
    query($lat: Float!, $lon: Float!, $radius: Float!, $startDate: DateTime!, $endDate: DateTime!) {
      results: keywordSearch(
        filter: { lat: $lat, lon: $lon, radius: $radius,
                  startDateRange: $startDate, endDateRange: $endDate, source: EVENTS }
        input: { first: 50 }
      ) {
        edges {
          node {
            result {
              ... on Event {
                title dateTime description eventUrl
                venue { name address city }
                feeSettings { amount currency }
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "lat": 48.8566, "lon": 2.3522, "radius": 25.0,
        "startDate": f"{date_from}T00:00:00",
        "endDate": f"{date_to}T23:59:59",
    }

    try:
        resp = requests.post(
            "https://api.meetup.com/gql",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[WARN] Meetup API error: {e}", file=sys.stderr)
        return []

    events = []
    for edge in data.get("data", {}).get("results", {}).get("edges", []):
        ev = edge.get("node", {}).get("result", {})
        if not ev.get("title"):
            continue

        fee = ev.get("feeSettings") or {}
        price_val = float(fee.get("amount", 0) or 0)
        if price_val > 50:
            continue

        venue = ev.get("venue") or {}
        dt = ev.get("dateTime", "")

        events.append({
            "title": ev["title"],
            "date": dt[:10],
            "time": dt[11:16],
            "venue": venue.get("name", ""),
            "address": ", ".join(filter(None, [venue.get("address"), venue.get("city")])),
            "type": "Meetup",
            "price": "Gratuit" if price_val == 0 else f"{price_val:.0f} {fee.get('currency', 'EUR')}",
            "url": ev.get("eventUrl", ""),
            "description": (ev.get("description") or "")[:250],
            "source": "meetup",
        })

    return events


# ---------------------------------------------------------------------------
# Luma scraping
# ---------------------------------------------------------------------------

def fetch_luma(date_from, date_to):
    session = requests.Session()
    session.headers.update(SESSION_HEADERS)

    try:
        resp = session.get("https://lu.ma/paris", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[WARN] Luma listing error: {e}", file=sys.stderr)
        return []

    # Extract event links from the page
    event_slugs = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Luma event links look like /slug or https://lu.ma/slug
        if href.startswith("/") and len(href) > 1 and "/" not in href[1:]:
            slug = href[1:]
            if slug not in ("paris", "discover", "signin", "signup", "create", "pricing"):
                event_slugs.add(slug)
        elif "lu.ma/" in href:
            parts = href.split("lu.ma/")
            if len(parts) == 2 and parts[1] and "/" not in parts[1]:
                slug = parts[1].split("?")[0]
                if slug not in ("paris", "discover", "signin", "signup", "create", "pricing"):
                    event_slugs.add(slug)

    events = []
    for slug in list(event_slugs)[:20]:
        time.sleep(0.5)
        ev = _fetch_luma_event(session, slug, date_from, date_to)
        if ev:
            events.append(ev)

    return events


def _fetch_luma_event(session, slug, date_from, date_to):
    try:
        resp = session.get(f"https://lu.ma/{slug}", timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try JSON-LD structured data first
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            # JSON-LD can be a single object or a list
            items = raw if isinstance(raw, list) else [raw]
            for data in items:
                if not isinstance(data, dict):
                    continue
                if data.get("@type") != "Event":
                    continue

                start = data.get("startDate", "")
                event_date = start[:10]
                if event_date < date_from or event_date > date_to:
                    return None

                location = data.get("location") or {}
                loc_addr = location.get("address") or {}
                raw_offers = data.get("offers") or {}
                if isinstance(raw_offers, list):
                    offers = raw_offers[0] if raw_offers else {}
                else:
                    offers = raw_offers
                price_val = float(offers.get("price", 0) or 0)
                if price_val > 50:
                    return None

                return {
                    "title": data.get("name", ""),
                    "date": event_date,
                    "time": start[11:16] if len(start) > 10 else "",
                    "venue": location.get("name", ""),
                    "address": ", ".join(filter(None, [
                        loc_addr.get("streetAddress", ""),
                        loc_addr.get("addressLocality", ""),
                    ])),
                    "type": "Meetup",
                    "price": "Gratuit" if price_val == 0 else f"{price_val:.0f} EUR",
                    "url": f"https://lu.ma/{slug}",
                    "description": (data.get("description") or "")[:250],
                    "source": "luma",
                }

        # Fallback: parse meta tags
        title_tag = soup.find("meta", property="og:title")
        desc_tag = soup.find("meta", property="og:description")
        if title_tag and title_tag.get("content"):
            return {
                "title": title_tag["content"],
                "date": date_from,  # approximate
                "time": "",
                "venue": "",
                "address": "Paris",
                "type": "Meetup",
                "price": "Voir le lien",
                "url": f"https://lu.ma/{slug}",
                "description": (desc_tag.get("content", "") if desc_tag else "")[:250],
                "source": "luma",
            }

    except Exception as e:
        print(f"[WARN] Luma event error ({slug}): {e}", file=sys.stderr)

    return None


# ---------------------------------------------------------------------------
# Filtering & deduplication
# ---------------------------------------------------------------------------

SOURCE_PRIORITY = {"eventbrite": 1, "meetup": 2, "luma": 3, "eventbrite_scrape": 4}


def filter_by_domains(events, domains):
    domains_lower = [d.lower() for d in domains]
    result = []
    for ev in events:
        text = (ev["title"] + " " + ev["description"]).lower()
        if any(d in text for d in domains_lower):
            result.append(ev)
    return result


def normalize_title(title):
    return re.sub(r"[^\w\s]", "", title.lower()).strip()


def deduplicate(events):
    events.sort(key=lambda e: SOURCE_PRIORITY.get(e["source"], 99))
    seen = []
    result = []
    for ev in events:
        norm = normalize_title(ev["title"])
        date = ev["date"]
        is_dup = False
        for s_norm, s_date in seen:
            if s_date == date and SequenceMatcher(None, norm, s_norm).ratio() > 0.75:
                is_dup = True
                break
        if not is_dup:
            seen.append((norm, date))
            result.append(ev)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch Paris tech/finance events")
    parser.add_argument("--from", dest="date_from", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", required=True, metavar="YYYY-MM-DD")
    args = parser.parse_args()

    config = load_config()
    domains = config.get("domains", [])

    # Fetch from all sources (each handles its own errors)
    events = fetch_eventbrite(args.date_from, args.date_to)
    events += fetch_meetup(args.date_from, args.date_to)
    events += fetch_luma(args.date_from, args.date_to)

    # Fallback: if Eventbrite API returned nothing, try scraping
    if not any(e["source"] == "eventbrite" for e in events):
        print("[INFO] Eventbrite API vide, tentative scraping...", file=sys.stderr)
        events += fetch_eventbrite_scrape(args.date_from, args.date_to)

    # Filter, dedup, sort
    events = filter_by_domains(events, domains)
    events = deduplicate(events)
    events.sort(key=lambda x: (x["date"], x["time"]))

    print(json.dumps(events, ensure_ascii=False, indent=2))
    print(f"[OK] {len(events)} evenement(s) trouve(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
