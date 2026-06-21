# Contract Lock (Claude authors changes; Codex checks before depending on a field)

Claude is the sole author of CONTRACTS/. To change a published contract:
1. Append `LOCKED <timestamp> — changing <field/topic>, reason ...`
2. Change CONTRACTS/, commit alone.
3. Append `UNLOCKED <timestamp> — what changed, what Codex must update.`

Codex: if the latest line is LOCKED, wait for UNLOCKED before building on it.

---
(no locks yet)
