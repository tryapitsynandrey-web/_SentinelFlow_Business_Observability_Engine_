FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY observability/ observability/
COPY runtime/ runtime/
COPY resilience/ resilience/
COPY persistence/ persistence/
COPY analytics/ analytics/
COPY config.yaml .

RUN pip install --no-cache-dir .

EXPOSE 9108 9109

CMD ["python", "-m", "src.main"]
