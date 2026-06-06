# Plans guide

This directory stores written plans and design notes for non-trivial work.

## Purpose

Use plans to capture proposed implementation steps, verification, and temporary reasoning before code changes happen.

Plans are not the long-term memory for repository rationale.
If a plan produces a lasting technical decision, promote that reasoning into `docs/decisions/`.
Final task reports should cite the decision record(s) consulted during the work, or explicitly say that none were relevant.

## Required rule for every non-trivial plan

Every plan must end with a final section named `Decision follow-up`.

That section must contain exactly one of these outcomes:

```md
## Decision follow-up

Decision record update required: `docs/decisions/000X-some-decision.md`
```

or

```md
## Decision follow-up

No durable decision change.
```

## Reusable template

For a copyable starting point, use `../templates/plan-template.md`.

## Minimal plan skeleton

```md
# <Title>

**Date:** YYYY-MM-DD

## Goal

## Planned changes

1. ...
2. ...

## Verification

- ...

## Decision follow-up

No durable decision change.
```
