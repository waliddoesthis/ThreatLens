# ThreatLens demo as a Hugging Face Space (Docker SDK). See docs/DEPLOY.md.
# Upload this file and the README.md next to it to the Space; nothing else is needed there.
# The image clones the public repository, builds the corpus and the index from the pinned
# sources, and starts the Streamlit app. The model is a hosted one, set in the Space settings.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000: everything the app writes must belong to that user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/user/hf
WORKDIR /home/user/app

# main, a tag or a commit: change it (Space settings > Variables, or here) to redeploy a version
ARG THREATLENS_REF=main
RUN git clone https://github.com/waliddoesthis/ThreatLens . && git checkout ${THREATLENS_REF}

# CPU-only torch: the Space has no GPU and the CUDA wheels are 4 GB larger
RUN pip install --user torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --user -e .

# Corpus and index are part of the image, built from the pinned versions (ingest/pins.py).
# The check fails the build if a source was unreachable, instead of shipping a partial demo.
RUN python -m threatlens.ingest.run \
    && python -m threatlens.index.build \
    && python deploy/space/check_index.py \
    && rm -rf data/raw

# The reranker is downloaded now, not by the first visitor
RUN python -c "from sentence_transformers import CrossEncoder; from threatlens.config import settings; CrossEncoder(settings.reranker_model)"

# Demo defaults; the model names and the API key come from the Space settings (docs/DEPLOY.md)
ENV DEMO_DAILY_LIMIT=300 \
    DEMO_SESSION_LIMIT=10 \
    HF_HUB_OFFLINE=1

EXPOSE 7860
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false", "--client.toolbarMode=minimal"]
