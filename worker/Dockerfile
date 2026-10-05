# Build context is the repository root: the worker needs the API's models and the prototype pipeline.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app:/app/api_src:/app/prototype
COPY worker/pyproject.toml worker/uv.lock ./
RUN uv sync --frozen --no-dev
COPY api/src ./api_src
COPY prototype/analyze.py prototype/analyze_rear.py ./prototype/
COPY worker/worker ./worker
# Pose models are downloaded by rtmlib on first use; bake them in so a cold container needs no network.
RUN uv run --no-sync python -c "from rtmlib import BodyWithFeet; [BodyWithFeet(mode=m, backend='onnxruntime', device='cpu') for m in ('performance', 'balanced')]"
CMD ["uv", "run", "--no-sync", "rq", "worker", "analysis", "--url", "redis://redis:6379/0"]
