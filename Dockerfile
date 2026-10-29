FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e .

COPY app ./app
COPY eval ./eval

EXPOSE 8000 8501
CMD ["uvicorn", "threatlens.api:app", "--host", "0.0.0.0", "--port", "8000"]
