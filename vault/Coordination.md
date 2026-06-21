# Coordination Rules (read once)

Both agents run in THIS ONE repo at the same time. That is safe ONLY because
their files never overlap. Hard ownership:

| Path          | Owner   | Other agent |
|---------------|---------|-------------|
| backend/      | Claude  | read-only   |
| CONTRACTS/    | Claude  | read-only   |
| frontend/     | Codex   | read-only   |
| vault logs    | per-file (each writes only its own) |

If you (the human) ever see a git merge conflict, an agent crossed the boundary.
That's the alarm. Re-read each manual's ownership table.

## Contract changes are serialized — see [[Contract Lock]].
