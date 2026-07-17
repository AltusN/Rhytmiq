# Scoring Polish Batch — Design

**Date:** 2026-07-17
**Scope:** Five small UX fixes to the Phase 1 meet-day scoring screen. Frontend only —
no backend changes (verified: `/meet-entries/` already filters by `age_group`, and
`Judge` already has `first_name`/`last_name`).

**Build split:** Items 1–4 implemented by Altus with Claude reviewing (tutor mode);
item 5 implemented by Claude because it interacts with `ScoringPage`'s keep-mounted
form-state machinery (`readyFormKey`).

**Process:** one `feature/scoring-polish` branch; one commit per item
(`feat:`/`fix:` prefix), with that item's tests in the same commit. Items are
independent; nominal order 1 → 5.

## Item 1 — Save feedback (`ScoreForm.tsx`)

After `saveScores` resolves with zero `boxErrors`, show a transient **"Saved ✓"**
beside the Save buttons. It clears after ~2 seconds or on the next edit, whichever
comes first.

- Must **not** appear when any box error came back — some writes landed, but a
  success indicator next to error text would be misleading. The inline box errors
  are the feedback in that case.
- Inline component state only (a timestamp/boolean plus a timeout). Deliberately
  **not** a toast system — Phase 2 builds that when the admin console needs it.

## Item 2 — Keyboard focus (`ScoreForm.tsx`)

Focus the **first visible, enabled** score box when the form mounts.

- `ScoreForm` is keyed by `(entry, apparatus)` in `ScoringPage`, so every
  competitor/apparatus switch is a fresh mount — mount-time focus covers both
  "picked a competitor" and "Save & next advanced" with one mechanism.
- "First" is dynamic: E-only levels start at E1; boxes whose panel slot has no
  judge are disabled and must be skipped.
- Enter-to-save already works (the form's `onSubmit` is Save & next); no change.

## Item 3 — Age-group filter (`CompetitorList.tsx`, `ScoringPage.tsx`)

Add an age-group select next to the existing level select, flowing to the entries
query exactly as `level` does today:

- Server-side filter (`?age_group=` on `/meet-entries/`), joined into the
  `["entries", meet.id, level, ageGroup]` query key.
- Changing it resets the selected competitor to `null`, same as level/apparatus.

## Item 4 — Panel display (`ScoringPage.tsx`)

- `judgeName` returns `first_name last_name` (was `last_name` only).
- Unassigned slots in the panel footer render visually distinct (amber text)
  rather than blending in as plain "unassigned".
- When the selected competitor's **required** slots include an unassigned one,
  show a one-line hint above the form with a link opening panel setup. (Today the
  setup link only renders when no competitor is selected — exactly when it isn't
  needed.) Required slots are the minimum viable panel — D, A, E1, E2 for full
  levels; E1, E2 for E-only levels — so legitimately-empty E3/E4 slots never
  trigger the hint, and E-only levels never warn about D/A.

## Item 5 — Unsaved-changes guard (`ScoreForm.tsx`, `ScoringPage.tsx`)

Confirm before discarding unsaved edits when switching competitor, level, or
apparatus.

- `ScoreForm` reports dirtiness upward via `onDirtyChange(isDirty)` (from RHF
  `formState.isDirty`).
- After a **fully successful** save, `ScoreForm` calls `reset(values)` to
  re-baseline cleanliness to the just-saved values (not to empty). Without this,
  `isDirty` stays true forever against the mount-time defaults and the guard would
  fire after every save. A partial failure leaves the form dirty — correct, since
  unsaved boxes remain.
- `ScoringPage` tracks `formDirty` and wraps the three switch paths (competitor
  select, level change, apparatus change) with
  `window.confirm("Discard unsaved scores?")`; declining aborts the switch before
  any state is set, so the `readyFormKey` machinery never sees a half-committed
  switch. Native `window.confirm` — no dialog component.
- **Scoped out:** guarding tab navigation (Scoring → Entries/Standings) and
  browser close/refresh. Both need router-blocking / `beforeunload` machinery in
  `MeetShell`, disproportionate to this batch. Revisit if accidental data loss is
  actually observed via those paths.

## Testing (Vitest + Testing Library + MSW; per-item, same commit)

1. **Save feedback:** appears after a clean save; absent when the save returns a
   box error; clears on next edit; timeout behavior with fake timers.
2. **Focus:** first focusable box focused on mount — normal level (D-Body),
   E-only level (E1), and disabled-first-slot (no D judge → skips to next
   enabled) cases.
3. **Age-group filter:** MSW asserts `age_group` reaches the API as a query
   param; changing the filter clears the current selection.
4. **Panel display:** full names in footer; hint renders only when a visible
   box's slot is unassigned (incl. the E-only case where D/A slots don't count).
5. **Dirty guard:** with `window.confirm` mocked — decline keeps the current form
   and its values; accept switches; after a clean save, switching does not
   prompt.

## Out of scope

- Toast system (Phase 2), itemized `PenaltyRecord` UI, tab/close navigation
  guards, any backend change.
