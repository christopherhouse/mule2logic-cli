# Testing Console Logging Output

## Problem
The API was processing requests successfully (200 responses) but there was no console output showing pipeline execution details. The orchestrator was logging at INFO level, but Python's logging wasn't configured, so logs were silently dropped.

## Solution
1. Added `_configure_logging()` function in `apps/api/src/m2la_api/telemetry/__init__.py` that:
   - Configures Python's root logger with `logging.basicConfig()`
   - Sets default log level to INFO (configurable via `LOG_LEVEL` env var)
   - Adds formatted StreamHandler to stdout
   - Uses `force=True` to override any existing configuration

2. Enhanced orchestrator logging in `services/agents/src/m2la_agents/orchestrator.py`:
   - Added pipeline start log with correlation ID, mode, and agent names
   - Added per-agent completion logs with status, duration, and reasoning summary
   - Added pipeline completion summary with final status and total duration

## Testing

### Expected Console Output

When running the API with a request, you should now see output like:

```
2026-04-14 23:00:00 [INFO] m2la_api.telemetry: Local-dev OTel configured with console exporters (service=m2la-api)
2026-04-14 23:01:15 [INFO] m2la_agents.orchestrator: Starting migration pipeline [correlation_id=abc-123, mode=project, agents=AnalyzerAgent, PlannerAgent]
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator: Workflow completed with 2 step(s)
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator: Agent 'AnalyzerAgent' completed with status=success in 3500.0ms
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator:   Reasoning: Analyzed 3 flows with 15 constructs...
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator: Agent 'PlannerAgent' completed with status=success in 1500.0ms
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator:   Reasoning: Mapped 12 supported constructs...
2026-04-14 23:01:20 [INFO] m2la_agents.orchestrator: Pipeline completed [correlation_id=abc-123, status=success, steps=2, duration=5000.0ms]
```

### Test Procedure

1. Start the API server:
   ```bash
   cd apps/api
   LOG_LEVEL=INFO uv run uvicorn m2la_api.main:app --reload
   ```

2. Run the CLI analyze command against a sample project:
   ```bash
   cd apps/cli
   npm run dev analyze ../packages/sample-projects/simple-http-logger
   ```

3. Observe console output on both API server and CLI:
   - **API console**: Should show detailed pipeline execution logs
   - **CLI console**: Should show user-friendly summary from response

### Log Level Control

The log level can be adjusted via the `LOG_LEVEL` environment variable:

```bash
# Debug mode (verbose)
LOG_LEVEL=DEBUG uv run m2la-api

# Info mode (default - shows pipeline execution)
LOG_LEVEL=INFO uv run m2la-api

# Warning mode (minimal - only warnings/errors)
LOG_LEVEL=WARNING uv run m2la-api
```

## Changes Made

1. `apps/api/src/m2la_api/telemetry/__init__.py`:
   - Added `import sys`
   - Added `_configure_logging()` function
   - Called `_configure_logging()` in `init_telemetry()` before OTel setup

2. `services/agents/src/m2la_agents/orchestrator.py`:
   - Added pipeline start log after building user message
   - Added per-agent completion logs in the metrics loop
   - Added pipeline completion summary before returning result

3. `README.md`:
   - Documented `LOG_LEVEL` environment variable
   - Documented `APPLICATIONINSIGHTS_CONNECTION_STRING` variable

## Verification

The changes ensure that:
- ✅ Python logging is properly configured when API starts
- ✅ INFO-level logs are written to stdout by default
- ✅ Log level is configurable via environment variable
- ✅ Pipeline execution is visible in console output
- ✅ Each agent step is logged with status and duration
- ✅ Reasoning summaries are included (truncated to 200 chars)
- ✅ Logging integrates with OpenTelemetry without conflicts
