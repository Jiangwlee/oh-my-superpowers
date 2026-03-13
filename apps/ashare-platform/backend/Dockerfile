FROM python:3.12-slim

WORKDIR /app
ENV ASHARE_PLATFORM_HOME=/app/runtime

COPY packages/ashare-data /app/packages/ashare-data
COPY apps/ashare-platform/backend/pyproject.toml /app/pyproject.toml
COPY apps/ashare-platform/backend/app /app/app

RUN python -m pip install --upgrade pip \
    && python -m pip install /app/packages/ashare-data \
    && python -m pip install .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
