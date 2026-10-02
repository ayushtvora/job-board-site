"""Cap how many requests are in flight to any one host at a time.

The runner scrapes companies in parallel, and many of them share an ATS
host: ~30 Greenhouse boards all hit boards-api.greenhouse.io, and the 60+
Workday tenants are spread over a handful of *.wdN.myworkdayjobs.com data
centres. Without a cap, parallel scrapes would multiply the request rate a
shared host sees from this server, which is what gets an IP rate-limited or
blocked.

Every scraper builds its own httpx client, so the cap is applied by wrapping
`httpx.Client.send`, the one method every request (including `httpx.get`)
goes through. The response body is read inside `send`, so a slot is held
until the whole response has arrived.
"""

import threading
from collections import defaultdict

import httpx

PER_HOST = 4
# Hosts sharing a suffix are one platform's servers, so they also share a
# limit across tenants (e.g. cisco.wd5... and paypal.wd1... are both Workday).
SHARED_SUFFIXES = {"myworkdayjobs.com": 8}

_lock = threading.Lock()
_semaphores: dict[str, threading.BoundedSemaphore] = {}
_original_send = httpx.Client.send
_installed = False


def install() -> None:
    global _installed
    with _lock:
        if _installed:
            return
        httpx.Client.send = _limited_send
        _installed = True


def _limited_send(self, request, *args, **kwargs):
    semaphores = _semaphores_for(request.url.host)
    for semaphore in semaphores:
        semaphore.acquire()
    try:
        return _original_send(self, request, *args, **kwargs)
    finally:
        for semaphore in reversed(semaphores):
            semaphore.release()


def _semaphores_for(host: str) -> list[threading.BoundedSemaphore]:
    # Always acquired in the same order (shared limit first, then the host's
    # own), so two threads can't each hold one and wait on the other.
    keys = [(suffix, limit) for suffix, limit in SHARED_SUFFIXES.items() if host.endswith("." + suffix)]
    keys.append((host, PER_HOST))
    with _lock:
        return [_semaphores.setdefault(key, threading.BoundedSemaphore(limit)) for key, limit in keys]
