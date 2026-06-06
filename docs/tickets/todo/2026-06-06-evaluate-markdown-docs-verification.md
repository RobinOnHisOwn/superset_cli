# Evaluate Markdown docs verification

- Status: todo
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-markdown-ticket-system.md`, `docs/decisions/0006-markdown-ticket-system.md`, `docs/tickets/README.md`

## Context

This repository now has a Markdown ticket system and a growing docs set, but there is no documented Markdown-specific verification step. During the ticket-system work, the docs were re-read manually, but no automated Markdown lint or link-check step was run. A small follow-up should evaluate whether the repo should adopt a lightweight docs verification command and where that command should be documented.

## Definition of done

- [ ] Identify the lightest acceptable Markdown verification approach for this repository.
- [ ] Decide whether the approach requires a new dependency or can use an existing tool.
- [ ] If adopted, document the command in the appropriate repo docs.
- [ ] If the approach changes repository workflow durably, update or add a decision record.

## Notes

This ticket is intended as the first real example ticket in the Markdown ticket system.
