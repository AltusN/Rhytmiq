import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { makeMeet } from "../../fixtures";
import { api, server } from "../../msw/server";
import { renderApp } from "../../utils";

const apparatusRow = {
  rank: 1,
  entry_id: 21,
  routine_id: 77,
  competitor_name: "Aletta van der Merwe",
  bib_number: "12",
  level: "senior",
  age_group: "o14",
  apparatus: "hoop",
  d_score: "14.20",
  a_score: "8.90",
  e_score: "8.25",
  penalty: "0.10",
  total: "31.25",
  medal: "gold",
};

const allAroundRow = {
  rank: 1,
  entry_id: 21,
  competitor_name: "Aletta van der Merwe",
  bib_number: "12",
  level: "senior",
  age_group: "o14",
  total: "94.10",
  e_total: "24.60",
  routines_counted: 3,
  medal: null,
};

function mockStandings({ provisional = true } = {}) {
  server.use(
    http.get(api("/meets/:meetId"), () =>
      HttpResponse.json(makeMeet({ id: 5, status: provisional ? "in_progress" : "completed" })),
    ),
    http.get(api("/districts/"), () => HttpResponse.json([])),
    http.get(api("/meets/:meetId/standings"), () =>
      HttpResponse.json({
        meet_id: 5,
        provisional,
        apparatus: "hoop",
        level: null,
        age_group: null,
        rankings: [apparatusRow],
      }),
    ),
    http.get(api("/meets/:meetId/all-around"), () =>
      HttpResponse.json({
        meet_id: 5,
        provisional,
        level: null,
        age_group: null,
        rankings: [allAroundRow],
      }),
    ),
  );
}

test("renders apparatus standings with scores and a provisional badge", async () => {
  mockStandings();
  renderApp("/meets/5/standings");
  expect(await screen.findByText("Aletta van der Merwe")).toBeInTheDocument();
  expect(screen.getByText("31.25")).toBeInTheDocument();
  expect(screen.getByText("gold")).toBeInTheDocument();
  expect(screen.getByText(/provisional/i)).toBeInTheDocument();
});

test("completed meet shows no provisional badge", async () => {
  mockStandings({ provisional: false });
  renderApp("/meets/5/standings");
  await screen.findByText("Aletta van der Merwe");
  expect(screen.queryByText(/provisional/i)).toBeNull();
});

test("all-around mode shows summed totals and routines counted", async () => {
  mockStandings();
  renderApp("/meets/5/standings");
  await screen.findByText("Aletta van der Merwe");
  await userEvent.click(screen.getByRole("button", { name: "All-around" }));
  expect(await screen.findByText("94.10")).toBeInTheDocument();
  expect(screen.getByText("3")).toBeInTheDocument();
});

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
      penalty: "0.30",
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
