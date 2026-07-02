FROM python:3.11-slim

# PYTHONDONTWRITEBYTECODE: no .pyc writes (AMP runs with a read-only root fs).
# HOME: AMP forces uid 65534 (nobody), whose passwd home is /nonexistent; the
# platform mounts a writable emptyDir at /home/nobody/.cache, so point HOME
# there for libraries that cache under ~/.cache (e.g. tiktoken).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/nobody

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# AMP's build pipeline rejects images without an explicit non-root USER, and
# the platform runs agent pods as uid 65534 (nobody) regardless — declare the
# same uid so build-time checks and runtime behavior match.
USER 10001

# OPENAI_API_KEY should be supplied at runtime (AMP: add it as an env var on
# the deploy page). Without it the server still starts; /chat reports the
# missing key and the !file mount check keeps working.
#
# amp-instrument enables zero-code tracing: it reads AMP_OTEL_ENDPOINT and
# AMP_AGENT_API_KEY (injected by the platform) and exports LangChain spans via
# OTLP. If those vars are absent (e.g. local run) it logs an error to stderr
# and the app runs untraced — it never blocks startup.
EXPOSE 8000
CMD ["amp-instrument", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
