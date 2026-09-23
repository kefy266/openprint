FROM python:3.12-slim

# Install CUPS, IPP utilities and printing dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cups \
    cups-client \
    cups-ipp-utils \
    cups-filters \
    ghostscript \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Web Port & CUPS
EXPOSE 5050 631

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5050", "backend.app:app"]
