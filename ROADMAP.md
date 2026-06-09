# AgentScope — Roadmap

## Priority Score: 92/100
Impact: 5.0 | Novelty: 4.5 | Virality: 5.0

## Milestones

### Month 1–2: Capture & Store
- [ ] OTel/OpenInference emitter library (Python)
- [ ] Local artifact store (filesystem-based)
- [ ] Basic CLI to view captured run metadata
- [ ] Redaction pipeline for common secret patterns

### Month 2–3: Replay UI
- [ ] React web app with timeline scrubber
- [ ] Diff viewer for file changes
- [ ] Tool call inspector with arguments/results
- [ ] Side-by-side run comparison view

### Month 3–4: Adapters
- [ ] Continue adapter (intercept MCP/chat calls)
- [ ] Aider adapter (wrap CLI invocation)
- [ ] Adapter template for community contributions

### Month 4–6: Team Mode
- [ ] Docker Compose stack (collector + Postgres + UI)
- [ ] Authentication (basic → SSO)
- [ ] S3-compatible artifact storage adapter
- [ ] Run sharing and commenting

## Effort
- Solo MVP: 3–4 PM
- Team of 3: 5–6.5 PM (~6–8 weeks elapsed)

## Demo Plan
1. Run Aider on a real bug → capture with AgentScope
2. Make agent fail on purpose → show the trace
3. Compare good vs bad run → post clip on X
