# AgentScope — Architecture

## Stack
- **Emitter/SDK**: TypeScript or Python library that wraps agent workflows
- **Trace Storage**: OTLP collector → Postgres (or ClickHouse for scale)
- **Large Artifacts**: Local filesystem or S3-compatible storage
- **Replay UI**: React web app
- **Deployment**: Single-user local mode (SQLite + files), team mode (Docker Compose + Postgres)

## Data Flow
```
Agent SDK Shim → OTLP Spans → Collector → Postgres/ClickHouse
                                  ↓
                              Artifacts (S3/local)
                                  ↓
                            Replay UI (React)
```

## MVP Scope (3–4 PM solo, 5–6.5 PM team of 3)
1. OTel/OpenInference capture emitter (Python SDK)
2. Local artifact store (filesystem)
3. Replay UI: timeline scrubber, diff viewer, tool call inspector
4. Two adapters: Continue + OpenHours (or Aider)

## OpenTelemetry / OpenInference Mapping
- LLM request/response → OTel GenAI span
- Tool calls → OTel tool span (already defined in OpenInference)
- File diffs → custom span attributes
- Git state → span events
- Test results → span events with attributes

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Secret leakage | Opinionated redaction pipeline, default local-first |
| Span explosion | Sampling config, configurable verbosity levels |
| Instrumentation churn | Internal trace schema versioning, map to OTel at boundary |
| OTel GenAI semantics still evolving | Abstract behind internal schema, upgrade mapping layer |
