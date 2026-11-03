FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY requirements.txt requirements.lock .
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock && pip check
COPY . .
CMD ["python", "-m", "src.pipeline", "--dataset", "data/clean"]
