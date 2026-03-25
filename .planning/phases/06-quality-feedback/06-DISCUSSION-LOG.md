# Phase 6: Quality & Feedback - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-25
**Phase:** 06-quality-feedback
**Areas discussed:** Dedup strategy, Feedback style, Error page design
**Mode:** Auto

---

## Dedup Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Dedup in polling service | Check before saving, compare route+date+price+airline | Yes |
| Dedup in database (unique constraint) | DB rejects duplicates | |
| Dedup in API client | Filter duplicates from SerpAPI response | |

**User's choice:** [auto] Dedup in polling service
**Notes:** Fix at the right layer, no schema change needed.

---

## Feedback Style

| Option | Description | Selected |
|--------|-------------|----------|
| Flash via query param | ?msg=grupo_criado on redirect, template renders | Yes |
| Session-based flash | Server-side session storage | |
| Toast notifications (JS) | JS-powered toast messages | |

**User's choice:** [auto] Flash via query param
**Notes:** Simplest, no JS, aligns with PRG pattern.

---

## Error Page Design

| Option | Description | Selected |
|--------|-------------|----------|
| Static HTML with back button | Friendly message, no tech details | Yes |
| Detailed error page | Show error code and description | |
| Redirect to home | Just redirect, no error page | |

**User's choice:** [auto] Static HTML with back button
**Notes:** No technical info exposed, friendly tone in Portuguese.

## Claude's Discretion

- Exact feedback message text
- Error page visual style
- Dedup comparison strategy details
