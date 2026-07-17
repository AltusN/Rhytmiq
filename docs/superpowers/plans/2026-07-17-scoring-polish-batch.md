# Scoring Polish Batch Implementation Plan

> **For agentic workers:** This plan is executed **interactively, in-session** — do
> NOT dispatch subagents. Tasks 1–4 are implemented by **Altus** (tutor mode: Claude
> reviews, challenges, and suggests alternatives, but does not write the code). Task 5
> is implemented by **Claude**. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Five small UX fixes to the Phase 1 meet-day scoring screen — save feedback,
keyboard focus, an age-group filter, panel display polish, and an unsaved-changes
guard.

**Architecture:** All changes live in `frontend/src/features/scoring/`. No backend
changes (`/meet-entries/` already filters by `age_group`; `Judge` already has
`first_name`/`last_name`). Each item is one commit with its tests, per the
test-after-each-module rule.

**Tech Stack:** React 19, React Hook Form, TanStack Query, Tailwind classes,
Vitest + Testing Library + MSW.

**Spec:** `docs/superpowers/specs/2026-07-17-scoring-polish-design.md`

## Global Constraints

- Branch: `feature/scoring-polish` off `main`. One commit per task, subject prefixed
  `feat:`/`fix:`.
- Commands run from `frontend/`: single file
  `npm test -- --run test/features/scoring/ScoringPage.test.tsx`; full suite
  `npm test -- --run`; typecheck+build `npm run build`.
- Test conventions: `renderApp(route)` from `test/utils.tsx`; MSW `server.use(...)`
  with the `api()` path helper and fixtures from `test/fixtures.ts`
  (see `test/features/scoring/ScoringPage.test.tsx` — its `mockBase()` helper is the
  starting point for every new ScoringPage-level test). Vitest globals are on
  (`test`, `expect`, `vi` need no import).
- The default test panel is `savePanel(5, { D: 1, E1: 2 })` — judge 1 (Naledi
  Dlamini) on D, judge 2 (Mina Kim) on E1; A and E2–E4 unassigned.
- No new dependencies.

## Setup

- [ ] `git checkout -b feature/scoring-polish` (from repo root, on a clean `main`)

---

### Task 1: Save feedback — "Saved ✓" indicator (Altus)

**Files:**
- Modify: `frontend/src/features/scoring/ScoreForm.tsx`
- Test: `frontend/test/features/scoring/ScoringPage.test.tsx`

**Interfaces:**
- Consumes: `saveScores` result (`result.boxErrors`, already in `submit`).
- Produces: a visible text node matching `/Saved ✓/` after a fully clean save.
  **Task 5 depends on this exact text** to await save completion in its tests —
  keep the copy `Saved ✓`.

**Behavior (from spec):** after `saveScores` resolves with zero `boxErrors`, show
"Saved ✓" beside the Save buttons; it disappears after ~2 s or on the next edit,
whichever comes first. It must NOT appear when any box error came back. Component
state only — no toast layer.

- [ ] **Step 1: Write the failing tests** in `ScoringPage.test.tsx` (they exercise
  the full page, matching the existing tests' style). Cover:
  1. Clean save (reuse the MSW POST handlers from the existing
     "save lazily creates the routine and posts scores" test) → `Saved ✓` appears.
  2. Save that returns a 409 box error (see the "partial failure" test's handlers)
     → `Saved ✓` is NOT in the document after the error renders.
  3. After a clean save, typing in a box removes the indicator.

  *Hints:* assert absence with `screen.queryByText(/Saved ✓/)` → `.toBeNull()`.
  For the 2 s auto-clear you can either use real timers with
  `await waitFor(() => …toBeNull(), { timeout: 3000 })`, or skip asserting the
  timeout entirely and only test clear-on-edit — mixing `vi.useFakeTimers()` with
  `userEvent` requires `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`
  and is fiddly; your call, but don't let the timer test flake.
- [ ] **Step 2: Run and verify they fail** —
  `npm test -- --run test/features/scoring/ScoringPage.test.tsx`, new tests FAIL
  (indicator never found).
- [ ] **Step 3: Implement in `ScoreForm.tsx`.** *Hints:* a `useState<boolean>`
  (or timestamp) set in `submit` only when `Object.keys(result.boxErrors).length
  === 0`; a `setTimeout` to clear it (clean up the timer — a `useEffect` return or
  ref); clear it on edit (RHF `watch` has a subscription form:
  `useEffect(() => { const sub = watch(() => …); return () => sub.unsubscribe(); }, [watch])`
  — or simpler, clear it inside the existing render-level `watch()` comparison you
  design). Render next to the buttons inside the existing `{!meetLocked && …}` block.
- [ ] **Step 4: Run tests, verify PASS** (same command).
- [ ] **Step 5: Commit** —
  `git add frontend/src/features/scoring/ScoreForm.tsx frontend/test/features/scoring/ScoringPage.test.tsx`
  `git commit -m "feat: saved indicator on clean score save"`

---

### Task 2: Keyboard focus on form mount (Altus)

**Files:**
- Modify: `frontend/src/features/scoring/ScoreForm.tsx`
- Test: `frontend/test/features/scoring/ScoringPage.test.tsx`

**Interfaces:**
- Consumes: `visibleBoxes` (already computed) — first entry with
  `judgeId !== undefined` is the focus target; RHF's `setFocus(name)` (destructure
  from the existing `useForm` call).
- Produces: no new exports; behavior only.

**Behavior (from spec):** on mount, focus the first **visible, enabled** score box.
`ScoreForm` is keyed by `(entry, apparatus)` in `ScoringPage`, so every
competitor/apparatus switch remounts it — mount-time focus covers both "picked a
competitor" and "Save & next advanced". Skip when `meetLocked` (all boxes disabled).

- [ ] **Step 1: Write the failing tests** in `ScoringPage.test.tsx`:
  1. Default panel, senior entry → `screen.getByLabelText("D-Body")` has focus
     (`.toHaveFocus()`).
  2. E-only entry (`level: "level_5"`, like the existing E-only test) → `E1` has
     focus.
  3. Panel with **no D judge** (`savePanel(5, { E1: 2 })` inside the test, after
     `localStorage.clear()`) → D-Body is disabled and `E1` has focus.
- [ ] **Step 2: Run and verify they fail** (focus lands on `document.body`).
- [ ] **Step 3: Implement.** *Hints:* a mount-only `useEffect` calling
  `setFocus(firstFocusableKey)` where
  `firstFocusableKey = visibleBoxes.find((b) => b.judgeId !== undefined)?.key`;
  guard `meetLocked` and the all-slots-unassigned case (`undefined` target). An
  empty dep array is correct here for the same reason `defaultValues` uses one —
  the component remounts per `(entry, apparatus)`.
- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat: focus first score box on competitor switch"`

---

### Task 3: Age-group filter (Altus)

**Files:**
- Modify: `frontend/src/features/scoring/CompetitorList.tsx`,
  `frontend/src/features/scoring/ScoringPage.tsx`
- Test: `frontend/test/features/scoring/ScoringPage.test.tsx` (page-level; add a
  select-rendering case to `frontend/test/features/scoring/CompetitorList.test.tsx`
  if you touch its props' rendering logic)

**Interfaces:**
- Consumes: `AGE_GROUPS` from `src/lib/domain.ts` (`["u8","u10","u12","u14","o14"]`);
  server filter `?age_group=` on `/meet-entries/`.
- Produces: `CompetitorList` gains props `ageGroup: string` and
  `onAgeGroupChange: (a: string) => void` (mirroring `level`/`onLevelChange`).
  The select's accessible name is **"Age group filter"** — Task 5's code references
  the handler shape. Entries query key becomes
  `["entries", meet.id, level, ageGroup]` — the `["entries", meet.id]` prefix must
  stay first so existing invalidations keep matching.

**Behavior (from spec):** an age-group select next to the level select, flowing to
the entries query exactly as `level` does (server-side, `age_group: ageGroup ||
undefined`, `""` = "All age groups"); changing it resets the selected competitor to
`null`.

- [ ] **Step 1: Write the failing tests** in `ScoringPage.test.tsx`:
  1. Capture the request:
     `http.get(api("/meet-entries/"), ({ request }) => { seenAgeGroup = new URL(request.url).searchParams.get("age_group"); return HttpResponse.json([…]); })`
     — select `o14` via
     `userEvent.selectOptions(screen.getByLabelText("Age group filter"), "o14")`,
     then `waitFor(() => expect(seenAgeGroup).toBe("o14"))`.
  2. With a competitor selected, changing the age group clears the selection
     ("Pick a competitor to score." reappears).
- [ ] **Step 2: Run and verify they fail** (no "Age group filter" element).
- [ ] **Step 3: Implement.** CompetitorList: copy the level `<select>` block, using
  `AGE_GROUPS` and label "Age group filter" (age-group codes like `u8`/`o14` read
  fine raw — `labelize` is a no-op on them, use it or not). ScoringPage: `ageGroup`
  state, extend the query key + `query` params, reset `selectedEntryId` in the
  change handler like `onLevelChange` does.
- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat: age-group filter on scoring competitor list"`

---

### Task 4: Panel display polish (Altus)

**Files:**
- Modify: `frontend/src/features/scoring/ScoringPage.tsx`
- Test: `frontend/test/features/scoring/ScoringPage.test.tsx`

**Interfaces:**
- Consumes: `judgesQ.data` (judges have `first_name` + `last_name`);
  `isEOnlyLevel` from `src/lib/score-math.ts`; `panel` state; `setPanelOpen`.
- Produces: no new exports; behavior only.

**Behavior (from spec):**
1. `judgeName` returns `first_name last_name` (was `last_name` only).
2. Unassigned slots in the panel footer render in amber (`text-amber-600`) instead
   of plain text.
3. When the selected competitor's **required** slots include an unassigned one,
   a one-line hint above the form links to panel setup. Required = minimum viable
   panel: `D, A, E1, E2` for full levels; `E1, E2` for E-only levels. E3/E4 never
   trigger it.

- [ ] **Step 1: Write the failing tests** in `ScoringPage.test.tsx`:
  1. Footer shows `Naledi Dlamini` (not just `Dlamini`) for slot D.
  2. Default panel (`{ D: 1, E1: 2 }`), senior selected → hint visible (A and E2
     are required-but-unassigned); it exposes a button/link whose click opens the
     panel dialog (assert the dialog's judge selects appear).
  3. Full minimum panel (`savePanel(5, { D: 1, A: 1, E1: 2, E2: 1 })`) → no hint,
     even though E3/E4 are unassigned.
  4. E-only entry with `{ E1: 2, E2: 1 }` and no D/A → no hint.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement.** *Hints:* a small helper in `ScoringPage.tsx` like
  `missingRequiredSlots(panel, level): string[]` keeps the JSX readable and is
  trivially testable through the page tests; reuse the existing
  `setPanelOpen(true)` button pattern for the hint's link. Amber: wrap the
  `judgeName(...)` output in a span with `text-amber-600` when the slot is
  `undefined`.
- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** —
  `git commit -m "feat: full judge names and unassigned-slot hint in panel display"`

---

### Task 5: Unsaved-changes guard (Claude)

**Files:**
- Modify: `frontend/src/features/scoring/ScoreForm.tsx`,
  `frontend/src/features/scoring/ScoringPage.tsx`
- Test: `frontend/test/features/scoring/ScoringPage.test.tsx`

**Interfaces:**
- Consumes: RHF `formState.isDirty` + `reset`; Task 1's `Saved ✓` indicator (to
  await save completion in tests); Task 3's `onAgeGroupChange` handler (gets
  guarded too).
- Produces: `ScoreForm` gains optional prop `onDirtyChange?: (dirty: boolean) => void`.

**Behavior (from spec):** `window.confirm("Discard unsaved scores?")` before a
competitor/level/apparatus/age-group switch while the form has unsaved edits;
declining aborts before any state changes. A fully clean save re-baselines the form
via `reset(values)` (partial failure stays dirty). Tab navigation and browser close
are scoped out.

- [ ] **Step 1: Write the failing tests** in `ScoringPage.test.tsx`:

```tsx
test("switching competitors with unsaved edits prompts; declining keeps the form", async () => {
  const second = makeEntry({ id: 22, meet_id: 5, gymnast_id: 7, group_id: null, level: "senior", bib_number: "13" });
  mockBase({ entries: [seniorEntry, second] });
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
  renderApp("/meets/5/scoring");
  await userEvent.click(await screen.findByRole("button", { name: /12 ·/ }));
  await userEvent.type(await screen.findByLabelText("E1"), "8.25");
  await userEvent.click(screen.getByRole("button", { name: /13 ·/ }));
  expect(confirmSpy).toHaveBeenCalledWith("Discard unsaved scores?");
  expect(screen.getByLabelText("E1")).toHaveValue("8.25"); // still bib 12's form

  confirmSpy.mockReturnValue(true);
  await userEvent.click(screen.getByRole("button", { name: /13 ·/ }));
  await waitFor(() => expect(screen.getByLabelText("E1")).toHaveValue(""));
  confirmSpy.mockRestore();
});

test("a clean save clears dirtiness, so switching does not prompt", async () => {
  const second = makeEntry({ id: 22, meet_id: 5, gymnast_id: 7, group_id: null, level: "senior", bib_number: "13" });
  mockBase({ entries: [seniorEntry, second] });
  server.use(
    http.post(api("/routines/"), () =>
      HttpResponse.json(makeRoutine({ id: 77, entry_id: 21 }), { status: 201 }),
    ),
    http.post(api("/judge-scores/"), () => HttpResponse.json({}, { status: 201 })),
  );
  const confirmSpy = vi.spyOn(window, "confirm");
  renderApp("/meets/5/scoring");
  await userEvent.click(await screen.findByRole("button", { name: /12 ·/ }));
  await userEvent.type(await screen.findByLabelText("E1"), "8.25");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await screen.findByText(/Saved ✓/); // Task 1's indicator marks completion
  await userEvent.click(screen.getByRole("button", { name: /13 ·/ }));
  expect(confirmSpy).not.toHaveBeenCalled();
  confirmSpy.mockRestore();
});
```

- [ ] **Step 2: Run and verify the first test fails** (no prompt appears; the
  switch goes through and E1 empties). The second test passes even before
  implementation — that's expected and fine: it pins the no-false-positive
  behavior (a clean save must never prompt) so a sloppy guard can't regress it.
- [ ] **Step 3: Implement `ScoreForm.tsx`** — add the prop, report dirtiness,
  re-baseline on clean save:

```tsx
// prop addition
onDirtyChange?: (dirty: boolean) => void;

// add `reset` to the existing useForm destructure (which by now also
// includes Task 2's `setFocus`) — don't drop anything already there

// report dirtiness upward (place after the useForm call)
const { isDirty } = formState;
useEffect(() => {
  onDirtyChange?.(isDirty);
}, [isDirty, onDirtyChange]);

// in submit, replace the boxErrors/onSaved tail with:
const clean = Object.keys(result.boxErrors).length === 0;
if (clean) reset(values); // re-baseline to just-saved values, not to empty
for (const [key, message] of Object.entries(result.boxErrors)) {
  setError(key as BoxKey | "penalty", { type: "server", message });
}
onSaved(result, next && clean);
```

  (Keep Task 1's saved-indicator call in the `clean` branch, adjacent to
  `reset(values)`. `useEffect` joins the existing `useMemo`/`useState` imports.)

- [ ] **Step 4: Implement `ScoringPage.tsx`** — track dirtiness, guard the four
  switch paths:

```tsx
const [formDirty, setFormDirty] = useState(false);
const confirmDiscard = () =>
  !formDirty || window.confirm("Discard unsaved scores?");

// CompetitorList handlers become:
onSelect={(entry) => {
  if (entry.id === selectedEntryId) return;
  if (!confirmDiscard()) return;
  setFormDirty(false);
  setSelectedEntryId(entry.id);
}}
onLevelChange={(l) => {
  if (!confirmDiscard()) return;
  setFormDirty(false);
  setLevel(l);
  setSelectedEntryId(null);
}}
onApparatusChange={(a) => {
  if (!confirmDiscard()) return;
  setFormDirty(false);
  setApparatus(a as Apparatus);
  setSelectedEntryId(null);
}}
onAgeGroupChange={(a) => {   // added in Task 3
  if (!confirmDiscard()) return;
  setFormDirty(false);
  setAgeGroup(a);
  setSelectedEntryId(null);
}}

// ScoreForm gains:
onDirtyChange={setFormDirty}
```

  The guard runs **before** any `set*` call, so the `readyFormKey` keep-mounted
  machinery never sees a half-committed switch. `setFormDirty(false)` on accepted
  switches avoids a stale `true` when no form mounts next (selection cleared).

- [ ] **Step 5: Run the new tests, verify PASS** —
  `npm test -- --run test/features/scoring/ScoringPage.test.tsx`
- [ ] **Step 6: Commit** —
  `git add frontend/src/features/scoring/ScoreForm.tsx frontend/src/features/scoring/ScoringPage.tsx frontend/test/features/scoring/ScoringPage.test.tsx`
  `git commit -m "feat: confirm before discarding unsaved score edits"`

---

### Task 6: Batch verification & wrap-up

- [ ] **Step 1: Full frontend suite + build** — from `frontend/`:
  `npm test -- --run && npm run build` → all tests PASS, build exits 0.
- [ ] **Step 2: Backend untouched** — from `backend/`: `.venv/bin/pytest -q` →
  same pass count as `main` (no backend files changed; `git diff main --stat`
  shows only `frontend/` + docs).
- [ ] **Step 3: Manual walkthrough** (backend + `npm run dev` running, seeded
  data): pick a competitor → boxes focused; type a score, switch competitor →
  prompt; save → `Saved ✓`, switch → no prompt; filter by age group; break the
  panel (remove A) → hint appears, link opens dialog.
- [ ] **Step 4:** Use superpowers:finishing-a-development-branch to merge/PR.
