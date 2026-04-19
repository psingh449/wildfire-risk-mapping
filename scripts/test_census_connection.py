"""Quick check that api.census.gov returns JSON (run on your machine where VPN applies)."""
import sys
import urllib.request

URL = (
    "https://api.census.gov/data/2020/dec/pl"
    "?get=P1_001N,NAME,state,county,tract,block%20group"
    "&for=block%20group:*&in=state:06%20county:07"
)


def main():
    req = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "wildfire-risk-mapping/1.0 (connectivity test)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        print(f"HTTP {resp.status}, {len(body)} bytes")
        print(body[:500].decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("FAILED:", e)
        sys.exit(1)
