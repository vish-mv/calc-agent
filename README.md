# Calc Agent

A small LangChain tool-calling agent (calculator + DuckDuckGo web search)
wrapped in a FastAPI server, used as a **Docker-type API agent** for testing
the Agent Management Platform sandbox isolation tiers (runc / gVisor / Kata).

## Endpoints

| Method | Path       | Description                                       |
|--------|------------|---------------------------------------------------|
| GET    | `/healthz` | Liveness probe                                    |
| POST   | `/chat`    | `{"session_id": "s1", "message": "..."}` → answer  |

Special chat commands:

- `!file` — reads the file at `FILE_CHECK_PATH` (default
  `/config/instructions.txt`) and returns its contents. Used to validate
  console **file mounts** on each isolation tier.

## Deploying on AMP (Docker agent)

1. Push this repo to GitHub.
2. Create an agent in the console with **Docker** build type, pointing at this
   repo / `Dockerfile`.
3. Endpoint config: **port `8000`**, **base path `/`**.
4. (Optional) Add `OPENAI_API_KEY` as an env var on the deploy page — without
   it the server still runs and `!file` works; `/chat` just reports the
   missing key instead of calling the LLM.
5. To test file mounts: add a console file mount at
   `/config/instructions.txt`, then send `!file` via Try It.

## Local usage

```bash
pip install -r requirements.txt

# HTTP server
uvicorn server:app --host 0.0.0.0 --port 8000

# Or the original CLI
python agent.py "What is 12345 * 678?"
```

## Tracing

Docker agents wire their own tracing. This image runs under
`amp-instrument` (from `amp-instrumentation==0.3.0` — the version must match
the platform's instrumentation version), which reads the platform-injected
`AMP_OTEL_ENDPOINT` / `AMP_AGENT_API_KEY` env vars and exports LangChain
spans automatically. On successful init the runtime logs show:

    WSO2 AMP instrumentation initialized successfully

If the env vars are absent (local runs), an error is logged and the app runs
untraced — startup is never blocked.

## Sandbox compatibility notes

The AMP sandbox runs containers as uid 65534 with a read-only root
filesystem; only `/tmp`, `/data`, and `/home/nobody/.cache` are writable. The
Dockerfile sets `HOME=/home/nobody` so libraries that cache under `~/.cache`
keep working, and `PYTHONDONTWRITEBYTECODE=1` avoids `.pyc` writes.
