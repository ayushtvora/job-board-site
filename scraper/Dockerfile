FROM python:3.12-slim

WORKDIR /app

# Playwright's bundled Node driver needs libatomic, which the slim image
# lacks (`playwright install` exits 127 without it, seen 2026-11-10).
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Only scrapers/meta.py and scrapers/uber.py need a real browser
# (metacareers.com and jobs.uber.com block plain HTTP clients at the
# TLS/HTTP2 fingerprint level) — every other scraper is lightweight httpx. --with-deps pulls in Chromium's system libraries too,
# which works here because this image has no USER directive (runs as root).
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]
