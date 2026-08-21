# Dockerfile — L4L-Bot credit farmer (Playwright edition)
# Playwright bundles its own Chromium — no Chrome/ChromeDriver needed
FROM python:3.11-slim

# Install only the lightweight libs Playwright needs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    libxshmfence1 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's bundled Chromium
RUN playwright install chromium --with-deps

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "farmer.py"]
