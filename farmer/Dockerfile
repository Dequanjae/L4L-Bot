# Use a proven Selenium Chrome base image instead of building from scratch
FROM selenium/standalone-chrome:latest

# Switch to root to install Python
USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "farmer.py"]
