FROM python:3.12-slim

WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY . .

CMD ["python", "news_aggregator/monitor.py"]

