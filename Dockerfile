FROM python:3.12-slim

WORKDIR /app

# Copy project definition
COPY pyproject.toml README.md ./
COPY collector/ collector/
COPY sdk/ sdk/

# Install dependencies
RUN pip install --no-cache-dir -e .

EXPOSE 8000

ENV DATABASE_URL="postgresql://traceforge:traceforge_dev_pass@postgres:5432/traceforge"

CMD ["uvicorn", "collector.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
