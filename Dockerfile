FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/app/data/hf

# CPU-only torch keeps the image ~1.5 GB instead of ~6 GB with CUDA wheels.
# Override with --build-arg TORCH_INDEX_URL=https://pypi.org/simple if that index is blocked.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install torch --index-url ${TORCH_INDEX_URL}

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e .

COPY app ./app
COPY eval ./eval

EXPOSE 8000 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "threatlens.api:app", "--host", "0.0.0.0", "--port", "8000"]
