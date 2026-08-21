FROM python:3.11-slim

# Install Chrome + deps
RUN apt-get update && apt-get install -y \
    wget gnupg2 unzip curl \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 \
    libxss1 libgtk-3-0 libasound2 libx11-xcb1 \
    libxcb-dpy3 libxcomposite1 libxdamage1 \
    libxrandr2 libatk1.0-0 libatk-bridge2.0-0 \
    libpangocairo-1.0-0 libpango-1.0-0 \
    libcairo2 libgbm1 libdrm2 libxshmfence1 \
    fonts-liberation xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (use wget for keyring, avoid apt-key deprecation)
RUN wget -q -O /tmp/google-chrome-key.asc https://dl.google.com/linux/linux_signing_key.pub && \
    gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg /tmp/google-chrome-key.asc && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.asc

# ChromeDriver is installed at runtime by webdriver-manager (pip package)

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "farmer.py"]
