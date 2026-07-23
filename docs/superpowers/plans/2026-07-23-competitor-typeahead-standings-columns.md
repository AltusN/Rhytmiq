# Competitor Typeahead + Band-Aware Standings Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two frontend meet-day fixes: (1) the apparatus standings table stops showing meaningless `0.00` D/A/E for bands that don't use those panels; (2) adding a competitor becomes a type-to-filter combobox instead of a long `<select>`.

**Architecture:** Both are frontend-only (React + Vite + Vitest/Testing Library); no backend, schema, or API change. Task 1 adapts the standings table per row via the existing `profileForLevel`. Task 2 adds a small self-contained `CompetitorCombobox` component (no new dependency) and wires it into `EntryCreateForm`.

**Tech Stack:** React 19, React Hook Form + Zod, TanStack Query, Vitest + Testing Library + MSW.

## Global Constraints

- **Frontend only.** No backend, schema, migration, OpenAPI, or `make types` change. The cutoff-medal behaviour for levels 1–3 on per-apparatus standings is already correct (`_apparatus_medal` returns `None`) and MUST NOT be touched.
- **No new npm dependency.** The combobox is a small controlled component, not react-select/Downshift (CLAUDE.md keeps deps minimal).
- **Match semantics (typeahead):** case-insensitive; an option matches when **any whitespace-separated part of its label starts with** the typed query; empty query matches all.
- **Band→panel mapping** comes from `profileForLevel(level).panels` (frontend `score-math.ts`): 1–3 → `["final"]`; 4–7 → `["difficulty_body","execution"]`; 8+ → all four. Never hard-code level lists.
- **Commit subjects start with a type prefix** (`feat:`/`fix:`/`docs:`/`test:`).

## File Structure

- `frontend/src/features/standings/StandingsPage.tsx` — per-row D/A/E rendering (Task 1).
- `frontend/test/features/standings/StandingsPage.test.tsx` — band-column tests (Task 1).
- `frontend/src/features/entries/CompetitorCombobox.tsx` — new component + `matchesNamePartPrefix` (Task 2).
- `frontend/src/features/entries/EntryCreateForm.tsx` — swap `<select>` for the combobox (Task 2).
- `frontend/test/features/entries/CompetitorCombobox.test.tsx` — new unit/component tests (Task 2).
- `frontend/test/features/entries/EntriesPage.test.tsx` — update the create-entry test to drive the combobox (Task 2).

The two tasks touch disjoint files and are independent; either can be reviewed and merged without the other.

---

## Task 1: Band-aware standings columns

**Files:**
- Modify: `frontend/src/features/standings/StandingsPage.tsx` (imports at top; apparatus `<tbody>` cells at lines 143-145)
- Test: `frontend/test/features/standings/StandingsPage.test.tsx`

**Interfaces:**
- Consumes: `profileForLevel(level: string) => { panels: string[] }` from `../../lib/score-math` (already exported).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write the failing tests**

In `frontend/test/features/standings/StandingsPage.test.tsx`, add a helper to mock a standings response with an arbitrary rankings array, then tests for a 1–3 row and an 8+ row. Mirror the existing `mockStandings` shape (a full row object like `apparatusRow`). Add near the other tests:

```typescript
function mockStandingsRows(rows: unknown[]) {
  server.use(
    http.get(api("/meets/:meetId"), () =>
      HttpResponse.json(makeMeet({ id: 5, status: "in_progress" })),
    ),
    http.get(api("/districts/"), () => HttpResponse.json([])),
    http.get(api("/meets/:meetId/standings"), () =>
      HttpResponse.json({
        meet_id: 5,
        provisional: true,
        apparatus: "freehand",
        level: null,
        age_group: null,
        rankings: rows,
      }),
    ),
    http.get(api("/meets/:meetId/all-around"), () =>
      HttpResponse.json({
        meet_id: 5,
        provisional: true,
        level: null,
        age_group: null,
        rankings: [],
      }),
    ),
  );
}

test("levels 1-3 apparatus rows show a dash for D/A/E and the mark in Total", async () => {
  mockStandingsRows([
    {
      rank: 1,
      entry_id: 1,
      routine_id: 55,
      competitor_name: "Leah Geyer",
      bib_number: "001",
      level: "level_1",
      age_group: "u9",
      apparatus: "freehand",
      d_score: "0.00",
      a_score: "0.00",
      e_score: "0.00",
      penalty: "0.00",
      total: "11.80",
      medal: null,
    },
  ]);
  renderApp("/meets/5/standings");

  const row = (await screen.findByText("Leah Geyer")).closest("tr")!;
  // D/A/E are not part of the 1-3 band, so they render as an em dash, not 0.00.
  expect(within(row).getAllByText("—")).toHaveLength(3);
  expect(within(row).queryByText("0.00")).toBeNull();
  expect(within(row).getByText("11.80")).toBeInTheDocument();
});

test("levels 8+ apparatus rows show numeric D/A/E", async () => {
  mockStandingsRows([
    {
      rank: 1,
      entry_id: 2,
      routine_id: 56,
      competitor_name: "Aletta van der Merwe",
      bib_number: "012",
      level: "senior",
      age_group: "o14",
      d_score: "14.20",
      a_score: "8.90",
      e_score: "8.25",
      penalty: "0.10",
      total: "31.25",
      medal: "gold",
    },
  ]);
  renderApp("/meets/5/standings");

  const row = (await screen.findByText("Aletta van der Merwe")).closest("tr")!;
  expect(within(row).getByText("14.20")).toBeInTheDocument();
  expect(within(row).getByText("8.90")).toBeInTheDocument();
  expect(within(row).getByText("8.25")).toBeInTheDocument();
  expect(within(row).queryByText("—")).toBeNull();
});
```

Add `within` to the Testing Library import at the top of the file: `import { screen, within } from "@testing-library/react";` (keep `userEvent` if already imported).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run test/features/standings/StandingsPage.test.tsx`
Expected: the 1–3 test FAILS — the current code renders `0.00` for D/A/E, so `getAllByText("—")` finds none and `queryByText("0.00")` is non-null. The 8+ test may already pass (numbers are shown today); that is fine.

- [ ] **Step 3: Add the band-aware helper and apply it in the apparatus rows**

In `frontend/src/features/standings/StandingsPage.tsx`, add `profileForLevel` to the `score-math` import (there is currently no import from it; add one):

```typescript
import { profileForLevel } from "../../lib/score-math";
```

Add a helper above the `StandingsPage` component (after the `fmt` definition, line 11):

```typescript
// D/A/E only mean something for the panels a row's band actually uses; showing 0.00 for a
// levels 1-3 routine (whose whole score is the single `final` mark) reads as a real zero.
// Render "—" for a panel the band doesn't score. Computed per row so a mixed "All levels"
// table renders each row by its own band.
const DASH = "—";
function panelCell(level: string, panels: string[], value: number | string): string {
  const active = profileForLevel(level).panels;
  return panels.some((p) => active.includes(p)) ? fmt(value) : DASH;
}
```

Replace the three D/A/E `<td>`s in the apparatus `<tbody>` (lines 143-145) with:

```typescript
                <td className="p-2 text-right">
                  {panelCell(row.level, ["difficulty_body", "difficulty_apparatus"], row.d_score)}
                </td>
                <td className="p-2 text-right">
                  {panelCell(row.level, ["artistry"], row.a_score)}
                </td>
                <td className="p-2 text-right">
                  {panelCell(row.level, ["execution"], row.e_score)}
                </td>
```

Leave the Rank/Bib/Competitor/Level/Pen/Total/Medal cells and the all-around table unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run test/features/standings/StandingsPage.test.tsx`
Expected: PASS — both new tests and the pre-existing standings tests (the existing senior row still shows `14.20/8.90/8.25`; `31.25` gold still renders).

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/altus/workspace/rhythmiq
git add frontend/src/features/standings/StandingsPage.tsx frontend/test/features/standings/StandingsPage.test.tsx
git commit -m "fix: standings shows a dash, not 0.00, for D/A/E panels a band doesn't use"
```

---

## Task 2: Competitor typeahead combobox

**Files:**
- Create: `frontend/src/features/entries/CompetitorCombobox.tsx`
- Modify: `frontend/src/features/entries/EntryCreateForm.tsx` (import + the Competitor `<label>` block at lines 87-106; clear selection on kind toggle)
- Test: `frontend/test/features/entries/CompetitorCombobox.test.tsx` (create), `frontend/test/features/entries/EntriesPage.test.tsx` (update the create-entry test)

**Interfaces:**
- Produces: `matchesNamePartPrefix(label: string, query: string): boolean` and a default-exported / named `CompetitorCombobox` component with props `{ options: {id: number; label: string}[]; value: string; onChange: (id: string) => void; ariaLabel?: string }`.
- Consumes in `EntryCreateForm`: RHF `watch("competitorId")` / `setValue("competitorId", id, { shouldValidate: true })`.

- [ ] **Step 1: Write the failing unit tests for the match function and the component**

Create `frontend/test/features/entries/CompetitorCombobox.test.tsx`:

```typescript
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { CompetitorCombobox, matchesNamePartPrefix } from "../../../src/features/entries/CompetitorCombobox";

describe("matchesNamePartPrefix", () => {
  it("matches when any name part starts with the query, case-insensitively", () => {
    expect(matchesNamePartPrefix("Leah Geyer", "Le")).toBe(true);
    expect(matchesNamePartPrefix("Leah Geyer", "ge")).toBe(true); // surname, case-insensitive
    expect(matchesNamePartPrefix("Leah Geyer", "ah")).toBe(false); // not a start
    expect(matchesNamePartPrefix("Leah Geyer", "")).toBe(true); // empty matches all
  });
});

function Harness({ options }: { options: { id: number; label: string }[] }) {
  const [value, setValue] = useState("");
  return (
    <>
      <CompetitorCombobox options={options} value={value} onChange={setValue} ariaLabel="Competitor" />
      <span data-testid="value">{value}</span>
    </>
  );
}

const OPTIONS = [
  { id: 7, label: "Leah Geyer" },
  { id: 8, label: "Liam Botha" },
  { id: 9, label: "Ella Johannes" },
];

it("filters the list as the user types and selects on click", async () => {
  const user = userEvent.setup();
  render(<Harness options={OPTIONS} />);

  await user.type(screen.getByLabelText("Competitor"), "Le");
  const list = screen.getByRole("listbox");
  expect(within(list).getByText("Leah Geyer")).toBeInTheDocument();
  expect(within(list).queryByText("Liam Botha")).toBeNull(); // "Li" would match, "Le" doesn't
  expect(within(list).queryByText("Ella Johannes")).toBeNull();

  await user.click(within(list).getByText("Leah Geyer"));
  expect(screen.getByTestId("value")).toHaveTextContent("7");
  expect(screen.getByLabelText("Competitor")).toHaveValue("Leah Geyer");
});

it("selects the highlighted option with the keyboard", async () => {
  const user = userEvent.setup();
  render(<Harness options={OPTIONS} />);

  const input = screen.getByLabelText("Competitor");
  await user.type(input, "Li"); // matches "Liam Botha"
  await user.keyboard("{ArrowDown}{Enter}");
  expect(screen.getByTestId("value")).toHaveTextContent("8");
});

it("closes the list on Escape without changing the value", async () => {
  const user = userEvent.setup();
  render(<Harness options={OPTIONS} />);

  await user.type(screen.getByLabelText("Competitor"), "Le");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("listbox")).toBeNull();
  expect(screen.getByTestId("value")).toHaveTextContent("");
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run test/features/entries/CompetitorCombobox.test.tsx`
Expected: FAIL — the module does not exist yet (`Failed to resolve import`).

- [ ] **Step 3: Create the `CompetitorCombobox` component**

Create `frontend/src/features/entries/CompetitorCombobox.tsx`:

```typescript
import { useEffect, useRef, useState } from "react";

export interface CompetitorComboboxOption {
  id: number;
  label: string;
}

/** Case-insensitive: any whitespace-separated part of `label` starts with `query`. */
export function matchesNamePartPrefix(label: string, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (q === "") return true;
  return label
    .toLowerCase()
    .split(/\s+/)
    .some((part) => part.startsWith(q));
}

export function CompetitorCombobox({
  options,
  value,
  onChange,
  ariaLabel = "Competitor",
}: {
  options: CompetitorComboboxOption[];
  value: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
}) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  // Keep the input text in sync with the externally-controlled value: fires only when a
  // selection is committed or the option list swaps (gymnast<->group), never on keystrokes
  // (those change `text`, not `value`).
  useEffect(() => {
    const selected = options.find((o) => String(o.id) === value);
    setText(selected ? selected.label : "");
  }, [value, options]);

  const selected = options.find((o) => String(o.id) === value);
  const q = text.trim();
  const showAll = q === "" || (selected != null && q === selected.label);
  const filtered = showAll ? options : options.filter((o) => matchesNamePartPrefix(o.label, q));

  function select(option: CompetitorComboboxOption) {
    onChange(String(option.id));
    setText(option.label);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-label={ariaLabel}
        value={text}
        autoComplete="off"
        className="mt-1 block w-full rounded border border-gray-300 p-1"
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setHighlight(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setHighlight((h) => Math.min(h + 1, filtered.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHighlight((h) => Math.max(h - 1, 0));
          } else if (e.key === "Enter") {
            if (open && filtered[highlight]) {
              e.preventDefault();
              select(filtered[highlight]);
            }
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && filtered.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded border border-gray-300 bg-white shadow"
        >
          {filtered.map((o, i) => (
            <li key={o.id} role="option" aria-selected={i === highlight}>
              <button
                type="button"
                // preventDefault keeps the input from blurring (which would close the
                // list) before the click registers and selects the option.
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => select(o)}
                onMouseEnter={() => setHighlight(i)}
                className={`block w-full px-2 py-1 text-left text-sm ${
                  i === highlight ? "bg-blue-100" : "bg-white"
                }`}
              >
                {o.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the component tests to verify they pass**

Run: `cd frontend && npx vitest run test/features/entries/CompetitorCombobox.test.tsx`
Expected: PASS — all four tests. If the click test fails because the list closed on blur, confirm the option's `onMouseDown={(e) => e.preventDefault()}` is present.

- [ ] **Step 5: Update the failing EntriesPage create-entry test first**

In `frontend/test/features/entries/EntriesPage.test.tsx`, the create-entry test (lines 43-47) uses `selectOptions(screen.getByLabelText("Competitor"), "7")`. The mocked gymnast is id 7, `"Lindiwe Nkosi"`. Replace the competitor-selection line with typing + picking from the combobox:

```typescript
  await userEvent.type(screen.getByLabelText("Competitor"), "Lin");
  await userEvent.click(await screen.findByText("Lindiwe Nkosi"));
  await userEvent.type(screen.getByLabelText("Bib number"), "31");
  await userEvent.selectOptions(screen.getByLabelText("Level"), "senior");
  await userEvent.selectOptions(screen.getByLabelText("Age group"), "o14");
  await userEvent.click(screen.getByRole("button", { name: "Create entry" }));
```

The POST-body assertion (gymnast_id 7, bib "31", level senior, age o14) is unchanged. Run it now to watch it fail against the still-present `<select>`:

Run: `cd frontend && npx vitest run test/features/entries/EntriesPage.test.tsx -t "creates a gymnast entry"`
Expected: FAIL — `getByLabelText("Competitor")` is still a `<select>`, so `type` + clicking `"Lindiwe Nkosi"` won't behave as a combobox (no listbox option to click).

- [ ] **Step 6: Wire the combobox into `EntryCreateForm`**

In `frontend/src/features/entries/EntryCreateForm.tsx`:

Add the import:

```typescript
import { CompetitorCombobox } from "./CompetitorCombobox";
```

Pull `setValue` from `useForm` (add it to the destructure at lines 34-35):

```typescript
  const { register, handleSubmit, watch, reset, setValue, formState } =
    useForm<EntryFormValues>({
```

Replace the Competitor `<label>` block (lines 87-106) with:

```typescript
      <label className="text-sm">
        Competitor
        <CompetitorCombobox
          ariaLabel="Competitor"
          value={watch("competitorId")}
          onChange={(id) => setValue("competitorId", id, { shouldValidate: true })}
          options={
            kind === "gymnast"
              ? gymnasts.map((g) => ({ id: g.id, label: `${g.first_name} ${g.last_name}` }))
              : groups.map((g) => ({ id: g.id, label: g.name }))
          }
        />
        {formState.errors.competitorId && (
          <span className="text-xs text-red-700">{formState.errors.competitorId.message}</span>
        )}
      </label>
```

Clear the selection when the Gymnast/Group toggle flips, so a stale gymnast id can't submit as a group. Update the two `kind` radios (lines 80-85) to clear on change (RHF's `register("kind")` still handles the value; add an `onChange` that also clears competitorId). Replace the fieldset (lines 79-86) with:

```typescript
      <fieldset className="flex gap-4">
        <label className="flex items-center gap-1 text-sm">
          <input
            type="radio"
            value="gymnast"
            {...register("kind", { onChange: () => setValue("competitorId", "") })}
          />{" "}
          Gymnast
        </label>
        <label className="flex items-center gap-1 text-sm">
          <input
            type="radio"
            value="group"
            {...register("kind", { onChange: () => setValue("competitorId", "") })}
          />{" "}
          Group
        </label>
      </fieldset>
```

(RHF merges the `onChange` option with its own handler, so `kind` still updates and the selection clears.)

- [ ] **Step 7: Run the updated EntriesPage test to verify it passes**

Run: `cd frontend && npx vitest run test/features/entries/EntriesPage.test.tsx`
Expected: PASS — the create-entry test now drives the combobox and the POST body still matches; the other EntriesPage tests are unaffected (the list-entries test doesn't open the form).

- [ ] **Step 8: Add the kind-toggle-clears-selection test**

Append to `frontend/test/features/entries/EntriesPage.test.tsx` a test proving the toggle clears a chosen gymnast (mirror the create test's setup up to selection):

```typescript
test("switching to Group clears a chosen gymnast", async () => {
  mockBase();
  renderApp("/meets/5/entries");
  await userEvent.click(await screen.findByRole("button", { name: "Add entry" }));

  await userEvent.type(screen.getByLabelText("Competitor"), "Lin");
  await userEvent.click(await screen.findByText("Lindiwe Nkosi"));
  expect(screen.getByLabelText("Competitor")).toHaveValue("Lindiwe Nkosi");

  await userEvent.click(screen.getByLabelText("Group"));
  expect(screen.getByLabelText("Competitor")).toHaveValue("");
});
```

Confirm the form is opened by an "Add entry" button (the page toggles `showForm`); if the button label or open flow differs, adjust the opening step to match the existing create-entry test's setup. If the create-entry test does not click "Add entry" (the form may render open), drop that line here too.

- [ ] **Step 9: Run the full frontend suite + build**

Run: `cd frontend && npm test -- --run && npm run build`
Expected: PASS — all test files green, build clean. If any other test used `selectOptions` on the Competitor control, update it to the combobox pattern (type + click the option).

- [ ] **Step 10: Commit**

```bash
cd /home/altus/workspace/rhythmiq
git add frontend/src/features/entries/CompetitorCombobox.tsx \
  frontend/src/features/entries/EntryCreateForm.tsx \
  frontend/test/features/entries/CompetitorCombobox.test.tsx \
  frontend/test/features/entries/EntriesPage.test.tsx
git commit -m "feat: type-to-filter competitor picker when adding an entry"
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-07-23-competitor-typeahead-standings-columns-design.md`):

| Spec item | Task |
|---|---|
| Item A (cutoff medal) needs no work | Global Constraints (untouched) |
| `CompetitorCombobox` with `{options, value, onChange, ariaLabel}` | Task 2 Step 3 |
| Filter = any name-part prefix, case-insensitive, empty→all | Task 2 Step 3 (`matchesNamePartPrefix`) |
| Select via click or Enter; ↑/↓ move; Esc closes | Task 2 Step 3 |
| Input shows selected label; typing re-filters | Task 2 Step 3 (`useEffect` on `[value, options]`) |
| No new dependency | Global Constraints |
| Wire into `EntryCreateForm` via `setValue`, keep zod contract | Task 2 Step 6 |
| Clear selection on Gymnast/Group toggle | Task 2 Step 6 + test Step 8 |
| Standings D/A/E → number or "—" per band via `profileForLevel` | Task 1 Step 3 |
| 1–3 → "—" for D/A/E; 4–7 → "—" for A; 8+ → all | Task 1 (mapping in `panelCell`) |
| Mixed "All levels" table renders each row by its band | Task 1 (per-row computation) |
| All-around table untouched; no "Final" column | Task 1 (only D/A/E cells changed) |
| Tests: `matchesNamePartPrefix`, combobox, EntriesPage, StandingsPage | Tasks 1 & 2 test steps |

**Placeholder scan:** every code step has complete code; every run step has a command and expected result. The two spots that ask the implementer to confirm existing test scaffolding (the "Add entry" open flow in Task 2 Step 8; whether the 8+ standings test already passes in Task 1 Step 2) state exactly what to check and the fallback.

**Type consistency:** `matchesNamePartPrefix(label, query)` signature is identical in the component and its tests. `CompetitorCombobox` props (`options: {id:number,label:string}[]`, `value: string`, `onChange: (id:string)=>void`, `ariaLabel`) match between definition, the test harness, and the `EntryCreateForm` call site. `panelCell(level, panels, value)` is defined and used only within `StandingsPage.tsx`. `profileForLevel(...).panels` (string[]) is the single source for band membership on both the standings and (indirectly) the scoring side.
