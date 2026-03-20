import argparse
import asyncio
import json
import statistics
import time
from typing import Dict, List, Optional

import requests
import websockets
from websockets.exceptions import ConnectionClosed
from urllib.parse import urlparse


async def one_worker(
    worker_id: int,
    url: str,
    cookie_header: str,
    duration_s: float,
    ping_interval_s: float,
    open_timeout_s: float,
    recv_timeout_s: float,
    results: List[Dict],
) -> None:
    start = time.perf_counter()
    connected_at = None
    pongs = 0
    recv_msgs = 0
    last_error: Optional[str] = None
    close_code: Optional[int] = None

    try:
        async with websockets.connect(
            url,
            additional_headers={"Cookie": cookie_header},
            open_timeout=open_timeout_s,
            ping_interval=None,  # we handle our own ping/pong
            close_timeout=5,
        ) as ws:
            connected_at = time.perf_counter()
            # Heartbeat loop: consumer replies with {"type":"pong"...}
            # Keep a dedicated read loop so we can count pongs.
            deadline = time.time() + duration_s

            next_ping = time.time()
            while time.time() < deadline:
                now = time.time()
                if now >= next_ping:
                    await ws.send(json.dumps({"type": "ping"}))
                    next_ping = now + ping_interval_s

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=recv_timeout_s)
                    recv_msgs += 1
                    try:
                        payload = json.loads(msg)
                        if payload.get("type") == "pong":
                            pongs += 1
                    except Exception:
                        # Ignore non-JSON or unexpected messages
                        pass
                except asyncio.TimeoutError:
                    # No message within recv_timeout; continue until deadline.
                    pass

            close_code = 1000

    except ConnectionClosed as e:
        close_code = e.code
        last_error = f"ConnectionClosed: code={e.code}, reason={e.reason!r}"
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
    finally:
        connected_ms = None
        if connected_at is not None:
            connected_ms = (connected_at - start) * 1000.0
        results.append(
            {
                "worker_id": worker_id,
                "connected_ms": connected_ms,
                "pongs": pongs,
                "recv_msgs": recv_msgs,
                "close_code": close_code,
                "error": last_error,
            }
        )


async def run_load(
    url: str,
    cookie_header: str,
    connections: int,
    duration_s: float,
    ping_interval_s: float,
    open_timeout_s: float,
    recv_timeout_s: float,
    concurrency_limit: Optional[int],
) -> List[Dict]:
    results: List[Dict] = []

    sem = asyncio.Semaphore(concurrency_limit or connections)

    async def sem_wrapper(i: int) -> None:
        async with sem:
            await one_worker(
                worker_id=i,
                url=url,
                cookie_header=cookie_header,
                duration_s=duration_s,
                ping_interval_s=ping_interval_s,
                open_timeout_s=open_timeout_s,
                recv_timeout_s=recv_timeout_s,
                results=results,
            )

    tasks = [asyncio.create_task(sem_wrapper(i)) for i in range(connections)]
    await asyncio.gather(*tasks)
    return results


def summarize(results: List[Dict]) -> None:
    total = len(results)
    ok = sum(1 for r in results if r["error"] is None)
    failed = total - ok

    connected_times = [r["connected_ms"] for r in results if r["connected_ms"] is not None]
    mean_connect = statistics.mean(connected_times) if connected_times else None
    p95_connect = None
    if connected_times:
        connected_times_sorted = sorted(connected_times)
        idx = int(0.95 * (len(connected_times_sorted) - 1))
        p95_connect = connected_times_sorted[idx]

    # Count non-1000 close codes (and 4001 for unauthorized if you see it)
    close_counts: Dict[str, int] = {}
    for r in results:
        code = r.get("close_code")
        key = str(code) if code is not None else "None"
        close_counts[key] = close_counts.get(key, 0) + 1

    print("\n=== WebSocket Load Test Summary ===")
    print(f"Total connections attempted: {total}")
    print(f"Connected without error:    {ok}")
    print(f"Failed:                     {failed}")
    if mean_connect is not None:
        print(f"Connect latency (ms): mean={mean_connect:.1f}, p95~={p95_connect:.1f}")
    print(f"Close codes observed: {close_counts}")
    sample_errors = [r for r in results if r["error"] is not None][:5]
    if sample_errors:
        print("Sample errors (first 5):")
        for r in sample_errors:
            print(f" - worker {r['worker_id']}: {r['error']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="ws://host:port/ws/notifications/")
    parser.add_argument(
        "--cookie",
        required=False,
        default="",
        help='Session cookie value or full cookie header, e.g. "abcd1234..." or "sessionid=abcd1234..."',
    )
    parser.add_argument("--cookie-name", default="sessionid", help="Django session cookie name (default: sessionid)")
    parser.add_argument(
        "--login-url",
        default="http://localhost:8000/accounts/login/",
        help="Login endpoint for session cookie auth (JSON body: username/password)",
    )
    parser.add_argument("--username", default="", help="If provided with --password, script will login to get session cookie")
    parser.add_argument("--password", default="", help="If provided with --username, script will login to get session cookie")
    parser.add_argument("--no-verify", action="store_true", help="Skip HTTP session verification before WS load")
    parser.add_argument("--connections", type=int, default=50, help="Number of websocket connections")
    parser.add_argument("--duration", type=float, default=60, help="How long to keep connections open (seconds)")
    parser.add_argument("--ping-interval", type=float, default=30, help="How often to send ping (seconds)")
    parser.add_argument("--open-timeout", type=float, default=10, help="WebSocket open timeout (seconds)")
    parser.add_argument("--recv-timeout", type=float, default=2.0, help="Recv timeout per loop (seconds)")
    parser.add_argument(
        "--concurrency-limit",
        type=int,
        default=0,
        help="Max concurrent connection attempts (0 = same as connections)",
    )

    args = parser.parse_args()

    cookie_header: str
    if args.username and args.password:
        # Acquire a fresh session cookie by logging in once, then reuse it for all WS connections.
        # NOTE: This uses JSON; accounts/views.user_login reads request.body when content_type == application/json.
        sess = requests.Session()
        login_payload = {"username": args.username, "password": args.password}
        r = sess.post(args.login_url, json=login_payload, timeout=30)
        if r.status_code >= 400:
            raise SystemExit(f"Login failed: HTTP {r.status_code}, body={r.text[:300]!r}")
        token = sess.cookies.get(args.cookie_name)
        if not token:
            # Fall back to full cookie jar string if cookie parsing didn't work.
            token = None
        if token:
            cookie_header = f"{args.cookie_name}={token}"
        else:
            # If we can't extract token, build Cookie header from cookie jar.
            cookie_header = "; ".join([f"{k}={v}" for k, v in sess.cookies.items()])
    else:
        if not args.cookie:
            raise SystemExit("Provide --cookie (sessionid) or use --username/--password for login mode.")
        # Backend authenticates WebSocket connections using Django's session cookie.
        # If you provide only the session token, convert it to "<cookie-name>=<token>".
        cookie_value = args.cookie.strip()
        cookie_header = cookie_value if "=" in cookie_value else f"{args.cookie_name}={cookie_value}"

    if not args.no_verify:
        # Verify that the cookie is actually authenticated for this server.
        # This prevents spending time on WS connections that will be rejected as anonymous.
        ws_u = urlparse(args.url)
        scheme = "https" if ws_u.scheme == "wss" else "http"
        base = f"{scheme}://{ws_u.hostname}:{ws_u.port or (443 if scheme == 'https' else 80)}"
        verify_url = f"{base}/accounts/sessiondata/"
        verify_r = requests.get(verify_url, headers={"Cookie": cookie_header}, timeout=15)
        if verify_r.status_code != 200:
            raise SystemExit(
                f"Session verification failed: HTTP {verify_r.status_code}, body={verify_r.text[:200]!r}\n"
                f"WebSocket connect will likely be rejected (anonymous). Re-login and copy the correct session cookie, or use --username/--password."
            )

    t0 = time.time()
    results = asyncio.run(
        run_load(
            url=args.url,
            cookie_header=cookie_header,
            connections=args.connections,
            duration_s=args.duration,
            ping_interval_s=args.ping_interval,
            open_timeout_s=args.open_timeout,
            recv_timeout_s=args.recv_timeout,
            concurrency_limit=(args.concurrency_limit or None),
        )
    )
    dt = time.time() - t0
    print(f"Run time: {dt:.1f}s")
    summarize(results)


if __name__ == "__main__":
    main()

