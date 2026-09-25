FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Only scrapers/meta.py needs a real browser (metacareers.com blocks plain
# HTTP clients at the TLS/HTTP2 fingerprint level) — every other scraper is
# lightweight httpx. --with-deps pulls in Chromium's system libraries too,
# which works here because this image has no USER directive (runs as root).
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]
