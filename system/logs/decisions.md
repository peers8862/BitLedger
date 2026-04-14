# Architectural Decision Log — BitLedger

Non-obvious decisions made during development. Read before touching encoder, decoder, or models.

Format:
```
## YYYY-MM-DD — [decision title]

**Decision:** [what was decided]

**Context:** [what situation prompted this]

**Why:** [the reasoning]

**Consequence:** [what this commits us to or rules out]
```

---

## 2026-04-14 — Adopted Workwarrior orchestrator system as dev control plane

**Decision:** Use the Workwarrior multi-agent orchestrator framework (roles, templates, gates, workflows, scripts) as the development control plane for BitLedger.

**Context:** Project initialization. Need a structured way to manage parallel agent work, task contracts, and quality gates.

**Why:** The framework provides proven patterns for: task card contracts (Gate A), test verification before merge (Gate B), and serialization safety for high-risk files. The generic infrastructure transfers cleanly; only project-specific content was replaced.

**Consequence:** All work follows the Orchestrator → Builder → Verifier → Docs handoff sequence. No implementation starts without a task card. No merge without Verifier sign-off.
