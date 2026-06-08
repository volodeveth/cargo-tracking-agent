FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY src ./src
COPY fixtures ./fixtures
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["uvicorn", "tracking_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
