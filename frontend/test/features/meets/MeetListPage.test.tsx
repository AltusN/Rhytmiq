import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { makeDistrict, makeMeet } from "../../fixtures";
import { api, server } from "../../msw/server";
import { renderApp } from "../../utils";

function seedDistricts() {
  server.use(
    http.get(api("/districts/"), () =>
      HttpResponse.json([makeDistrict({ id: 1, name: "Western Cape", abbreviation: "WC" })]),
    ),
  );
}

test("lists meets with status badges", async () => {
  server.use(
    http.get(api("/meets/"), () =>
      HttpResponse.json([
        makeMeet({ name: "Winter Cup", status: "in_progress" }),
        makeMeet({ name: "Spring Trials", status: "draft" }),
      ]),
    ),
  );
  server.use(http.get(api("/districts/"), () => HttpResponse.json([])));
  renderApp("/");
  expect(await screen.findByText("Winter Cup")).toBeInTheDocument();
  expect(screen.getByText("Spring Trials")).toBeInTheDocument();
  expect(screen.getByText("in progress")).toBeInTheDocument();
  expect(screen.getByText("draft")).toBeInTheDocument();
});

test("shows the API error detail on failure", async () => {
  server.use(
    http.get(api("/meets/"), () =>
      HttpResponse.json({ detail: "boom" }, { status: 500 }),
    ),
  );
  server.use(http.get(api("/districts/"), () => HttpResponse.json([])));
  renderApp("/");
  expect(await screen.findByRole("alert")).toHaveTextContent("boom");
});

test("meet name still navigates into the meet", async () => {
  seedDistricts();
  server.use(
    http.get(api("/meets/"), () => HttpResponse.json([makeMeet({ id: 4, name: "Spring Open" })])),
  );
  server.use(http.get(api("/meets/4"), () => HttpResponse.json(makeMeet({ id: 4, name: "Spring Open" }))));
  server.use(http.get(api("/meet-entries/"), () => HttpResponse.json([])));
  renderApp("/");
  await userEvent.click(await screen.findByRole("link", { name: /Spring Open/ }));
  expect(await screen.findByRole("heading", { name: /Spring Open/ })).toBeInTheDocument();
});

test("creates a meet without sending status", async () => {
  seedDistricts();
  server.use(http.get(api("/meets/"), () => HttpResponse.json([])));
  let posted: Record<string, unknown> | null = null;
  server.use(
    http.post(api("/meets/"), async ({ request }) => {
      posted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeMeet(), { status: 201 });
    }),
  );
  renderApp("/");
  await userEvent.click(await screen.findByRole("button", { name: "New meet" }));
  await userEvent.type(screen.getByLabelText("Name"), "Spring Open");
  await userEvent.type(screen.getByLabelText("Location"), "Cape Town");
  await userEvent.type(screen.getByLabelText("Start date"), "2026-09-01");
  await userEvent.type(screen.getByLabelText("End date"), "2026-09-02");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() =>
    expect(posted).toEqual({
      name: "Spring Open",
      location: "Cape Town",
      start_date: "2026-09-01",
      end_date: "2026-09-02",
      district_id: null,
      medal_gold_min: null,
      medal_silver_min: null,
    }),
  );
  expect(posted!).not.toHaveProperty("status");
});

test("blocks an end date before the start date", async () => {
  seedDistricts();
  server.use(http.get(api("/meets/"), () => HttpResponse.json([])));
  let called = false;
  server.use(
    http.post(api("/meets/"), () => {
      called = true;
      return HttpResponse.json(makeMeet(), { status: 201 });
    }),
  );
  renderApp("/");
  await userEvent.click(await screen.findByRole("button", { name: "New meet" }));
  await userEvent.type(screen.getByLabelText("Name"), "Spring Open");
  await userEvent.type(screen.getByLabelText("Location"), "Cape Town");
  await userEvent.type(screen.getByLabelText("Start date"), "2026-09-05");
  await userEvent.type(screen.getByLabelText("End date"), "2026-09-01");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("End date must be on or after the start date")).toBeInTheDocument();
  expect(called).toBe(false);
});

test("blocks a gold minimum that is not above the silver minimum", async () => {
  seedDistricts();
  server.use(http.get(api("/meets/"), () => HttpResponse.json([])));
  let called = false;
  server.use(
    http.post(api("/meets/"), () => {
      called = true;
      return HttpResponse.json(makeMeet(), { status: 201 });
    }),
  );
  renderApp("/");
  await userEvent.click(await screen.findByRole("button", { name: "New meet" }));
  await userEvent.type(screen.getByLabelText("Name"), "Spring Open");
  await userEvent.type(screen.getByLabelText("Location"), "Cape Town");
  await userEvent.type(screen.getByLabelText("Start date"), "2026-09-01");
  await userEvent.type(screen.getByLabelText("End date"), "2026-09-02");
  await userEvent.type(screen.getByLabelText("Gold minimum"), "8");
  await userEvent.type(screen.getByLabelText("Silver minimum"), "9");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("Gold minimum must be above silver")).toBeInTheDocument();
  expect(called).toBe(false);
});

test("blocks setting only one medal minimum", async () => {
  seedDistricts();
  server.use(http.get(api("/meets/"), () => HttpResponse.json([])));
  let called = false;
  server.use(
    http.post(api("/meets/"), () => {
      called = true;
      return HttpResponse.json(makeMeet(), { status: 201 });
    }),
  );
  renderApp("/");
  await userEvent.click(await screen.findByRole("button", { name: "New meet" }));
  await userEvent.type(screen.getByLabelText("Name"), "Spring Open");
  await userEvent.type(screen.getByLabelText("Location"), "Cape Town");
  await userEvent.type(screen.getByLabelText("Start date"), "2026-09-01");
  await userEvent.type(screen.getByLabelText("End date"), "2026-09-02");
  await userEvent.type(screen.getByLabelText("Gold minimum"), "9");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("Set both medal minimums or neither")).toBeInTheDocument();
  expect(called).toBe(false);
});
