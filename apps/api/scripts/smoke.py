"""A post-switch smoke check.

Run it against a deployed service with a known account and one library entry:

    python scripts/smoke.py --base http://127.0.0.1:8010 \
        --email probe@example.invalid --password … --entry 123

Each step prints one line; the exit code is non-zero if any of them fails. The steps
are the paths a browser hits first, so a failure here is a reason to point the host
back before anyone notices on their own.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def call(base: str, path: str, *, token: str = "", body: dict | None = None):
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--entry", type=int, default=0)
    args = parser.parse_args(argv)

    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        print(f"{'ok  ' if ok else 'FAIL'} {name}{(' ' + detail) if detail else ''}")
        if not ok:
            failures += 1

    status, _ = call(args.base, "/health/live/")
    check("liveness", status == 200, f"({status})")
    status, _ = call(args.base, "/health/ready/")
    check("readiness", status == 200, f"({status})")

    status, session = call(
        args.base,
        "/api/v1/auth/sessions/password/",
        body={"email": args.email, "password": args.password},
    )
    token = session.get("access", "") if isinstance(session, dict) else ""
    check("sign in", status == 200 and bool(token), f"({status})")
    if not token:
        return 1

    for path in (
        "/api/v1/users/me/profile/",
        "/api/v1/users/me/library/entries/",
        "/api/v1/community/me/notifications/",
        "/api/v1/community/me/feed/",
    ):
        status, _ = call(args.base, path, token=token)
        check(f"read {path}", status == 200, f"({status})")

    if args.entry:
        status, _ = call(
            args.base,
            f"/api/v1/users/me/library/entries/{args.entry}/",
            token=token,
        )
        check(f"read entry {args.entry}", status == 200, f"({status})")

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
