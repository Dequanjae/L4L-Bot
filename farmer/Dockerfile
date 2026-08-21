FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 \
    libxss1 libgtk-3-0 libasound2 libx11-xcb1 libxcb-dpy3 libxcomposite1 \
    libxdamage1 libxrandr2 libatk1.0-0 libatk-bridge2.0-0 \
    libpangocairo-1.0-0 libpango-1.0-0 libcairo2 libgbm1 libdrm2 \
    libxshmfence1 fonts-liberation xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "farmer.py"]
