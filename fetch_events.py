#!/usr/bin/env python3
"""Fetches tech/finance events in Paris from Eventbrite and Meetup APIs."""
import argparse
import json
import os
import sys
from datetime import datetime

import requests


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def fetch_eventbrite(date_from, date_to):
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        print("[WARN] EVENTBRITE_TOKEN non défini, Eventbrite ignoré.", file=sys.stderr)
        return []

    url = "https://www.eventbriteapi.com/v3/events/search/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "location.address": "Paris, France",
        "location.within": "15km",
        "start_date.range_start": f"{date_from}T00:00:00",
        "start_date.range_end": f"{date_to}T23:59:59",
        "categories": "102",
        "expand": "venue,ticket_availability",
        "page_size": 50,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[WARN] Eventbrite API error: {e}", file=sys.stderr)
        return []

    events = []
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

        events.append({
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

    return events


def fetch_meetup(date_from, date_to):
    token = os.environ.get("MEETUP_API_KEY")
    if not token:
        print("[WARN] MEETUP_API_KEY non défini, Meetup ignoré.", file=sys.stderr)
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


def filter_by_domains(events, domains):
    domains_lower = [d.lower() for d in domains]
    result = []
    for ev in events:
        text = (ev["title"] + " " + ev["description"]).lower()
        if any(d in text for d in domains_lower):
            result.append(ev)
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch Paris tech/finance events")
    parser.add_argument("--from", dest="date_from", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", required=True, metavar="YYYY-MM-DD")
    args = parser.parse_args()

    config = load_config()
    domains = config.get("domains", [])

    events = fetch_eventbrite(args.date_from, args.date_to)
    events += fetch_meetup(args.date_from, args.date_to)

    events = filter_by_domains(events, domains)
    events.sort(key=lambda x: (x["date"], x["time"]))

    print(json.dumps(events, ensure_ascii=False, indent=2))
    print(f"[OK] {len(events)} événement(s) trouvé(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
