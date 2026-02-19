#!/usr/bin/env python3
"""
Action 3: The Routing Cartel — Robinhood Q2 2024 XML (Wayback Machine)

Mission: Locate the Q2 2024 Rule 606 XML for Robinhood to identify
dynamic routing to alternative brokers (Jump Execution, StoneX, Comhar)
when Citadel's pipes were clogged during the May 2024 event.

Source: Wayback Machine CDX API searching for Robinhood 606 XML captures.
"""

import urllib.request
import json
import os

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results'
)


def search_wayback_cdx(url_pattern, output_fields="timestamp,original"):
    """Search Wayback Machine CDX index for URL captures."""
    cdx_url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url={url_pattern}&output=json&fl={output_fields}"
    )
    try:
        req = urllib.request.Request(cdx_url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        return data
    except Exception as e:
        print(f"  [-] CDX search failed: {e}")
        return None


def main():
    print("=" * 70)
    print("ROBINHOOD Q2 2024 RULE 606 ROUTING — WAYBACK MACHINE SEARCH")
    print("=" * 70)

    results = {
        "_metadata": {
            "title": "Robinhood Rule 606 XML — Wayback Machine Search",
            "date": "2026-02-18",
            "target": "Q2 2024 Rule 606(a) routing report XML"
        },
        "captures": [],
        "q2_2024_hits": []
    }

    # Search patterns for Robinhood 606 data
    search_patterns = [
        "cdn.robinhood.com/*606*.xml",
        "cdn.robinhood.com/*606*",
        "robinhood.com/*606*.xml",
        "robinhood.com/us/en/about/legal/order-routing*",
    ]

    for pattern in search_patterns:
        print(f"\n[*] Searching: {pattern}")
        data = search_wayback_cdx(pattern)

        if not data or len(data) <= 1:
            print(f"  [-] No results for pattern: {pattern}")
            continue

        print(f"  [+] Found {len(data) - 1} captures")

        for row in data[1:]:
            ts, orig = row[0], row[1]
            capture = {
                "timestamp": ts,
                "url": orig,
                "wayback_url": f"https://web.archive.org/web/{ts}/{orig}",
                "year_month": ts[:6]
            }
            results["captures"].append(capture)

            # Q2 2024 report would be published in July/August 2024
            if ts.startswith("202407") or ts.startswith("202408") or ts.startswith("202409"):
                print(f"\n  🚨 POTENTIAL Q2 2024 CAPTURE:")
                print(f"     Timestamp: {ts}")
                print(f"     Original:  {orig}")
                print(f"     Wayback:   {capture['wayback_url']}")
                print(f"     -> Download and grep for 'Jump Execution', 'StoneX', 'Comhar'")
                results["q2_2024_hits"].append(capture)

    # Also search for the direct 606 disclosure pages
    print("\n" + "-" * 70)
    print("[*] Searching for Robinhood regulatory disclosure pages...")
    disclosure_data = search_wayback_cdx("robinhood.com/us/en/about/legal/*")
    if disclosure_data and len(disclosure_data) > 1:
        for row in disclosure_data[1:]:
            ts, orig = row[0], row[1]
            if '606' in orig.lower() or 'order' in orig.lower():
                if ts.startswith("2024"):
                    capture = {
                        "timestamp": ts,
                        "url": orig,
                        "wayback_url": f"https://web.archive.org/web/{ts}/{orig}",
                        "year_month": ts[:6]
                    }
                    results["q2_2024_hits"].append(capture)
                    print(f"  [+] 2024 606 page: {capture['wayback_url']}")

    # Save
    out_path = os.path.join(RESULTS_DIR, 'robinhood_wayback_606.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to {out_path}")
    print(f"\n[✅] Search complete: {len(results['captures'])} total captures, "
          f"{len(results['q2_2024_hits'])} Q2 2024 hits")


if __name__ == "__main__":
    main()
