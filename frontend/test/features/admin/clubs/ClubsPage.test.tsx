import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { makeClub, makeDistrict } from "../../../fixtures";
import { api, server } from "../../../msw/server";
import { renderApp } from "../../../utils";

function mockBase(clubs: unknown[] = []) {
  server.use(
    http.get(api("/clubs/"), () => HttpResponse.json(clubs)),
    http.get(api("/districts/"), () =>
      HttpResponse.json([makeDistrict({ id: 1, name: "Western Cape" })]),
    ),
  );
}

test("lists clubs with their district name", async () => {
  mockBase([makeClub({ id: 5, name: "Star Gymnastics", abbreviation: "STAR", district_id: 1 })]);
  renderApp("/admin/clubs");
  expect(await screen.findByText("Star Gymnastics")).toBeInTheDocument();
  expect(screen.getByText("Western Cape")).toBeInTheDocument();
});

test("creates a club", async () => {
  mockBase();
  let posted: Record<string, unknown> | null = null;
  server.use(
    http.post(api("/clubs/"), async ({ request }) => {
      posted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeClub(), { status: 201 });
    }),
  );
  renderApp("/admin/clubs");
  await userEvent.click(await screen.findByRole("button", { name: "New club" }));
  await screen.findByText("Western Cape");
  await userEvent.type(screen.getByLabelText("Name"), "Acro Academy");
  await userEvent.type(screen.getByLabelText("Abbreviation"), "ACRO");
  await userEvent.selectOptions(screen.getByLabelText("District"), "1");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() =>
    expect(posted).toEqual({ name: "Acro Academy", abbreviation: "ACRO", district_id: 1 }),
  );
});

test("requires a district", async () => {
  mockBase();
  let called = false;
  server.use(
    http.post(api("/clubs/"), () => {
      called = true;
      return HttpResponse.json(makeClub(), { status: 201 });
    }),
  );
  renderApp("/admin/clubs");
  await userEvent.click(await screen.findByRole("button", { name: "New club" }));
  await screen.findByText("Western Cape");
  await userEvent.type(screen.getByLabelText("Name"), "Acro Academy");
  await userEvent.type(screen.getByLabelText("Abbreviation"), "ACRO");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("Pick a district")).toBeInTheDocument();
  expect(called).toBe(false);
});

test("edits a club, sending only the changed field", async () => {
  mockBase([makeClub({ id: 5, name: "Star Gymnastics", abbreviation: "STAR", district_id: 1 })]);
  let patched: Record<string, unknown> | null = null;
  server.use(
    http.patch(api("/clubs/:clubId"), async ({ request }) => {
      patched = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeClub({ id: 5 }));
    }),
  );
  renderApp("/admin/clubs");
  await userEvent.click(await screen.findByRole("button", { name: "Edit Star Gymnastics" }));
  const abbr = screen.getByLabelText("Abbreviation");
  await userEvent.clear(abbr);
  await userEvent.type(abbr, "STARS");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(patched).toEqual({ abbreviation: "STARS" }));
});

test("surfaces a 409 when a club still has dependents", async () => {
  mockBase([makeClub({ id: 5, name: "Star Gymnastics", district_id: 1 })]);
  server.use(
    http.delete(api("/clubs/:clubId"), () =>
      HttpResponse.json({ detail: "Cannot delete club with existing gymnasts" }, { status: 409 }),
    ),
  );
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  renderApp("/admin/clubs");
  await userEvent.click(await screen.findByRole("button", { name: "Delete Star Gymnastics" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("existing gymnasts");
  confirmSpy.mockRestore();
});

test("a delete error is cleared by a later successful save", async () => {
  mockBase([makeClub({ id: 5, name: "Star Gymnastics", abbreviation: "STAR", district_id: 1 })]);
  server.use(
    http.delete(api("/clubs/:clubId"), () =>
      HttpResponse.json({ detail: "Cannot delete club with existing gymnasts" }, { status: 409 }),
    ),
  );
  let patched: Record<string, unknown> | null = null;
  server.use(
    http.patch(api("/clubs/:clubId"), async ({ request }) => {
      patched = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeClub({ id: 5, name: "Star Gymnastics" }));
    }),
  );
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  renderApp("/admin/clubs");
  await userEvent.click(await screen.findByRole("button", { name: "Delete Star Gymnastics" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("existing gymnasts");

  await userEvent.click(screen.getByRole("button", { name: "Edit Star Gymnastics" }));
  const abbr = screen.getByLabelText("Abbreviation");
  await userEvent.clear(abbr);
  await userEvent.type(abbr, "STARS");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(patched).toEqual({ abbreviation: "STARS" }));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  confirmSpy.mockRestore();
});

test("surfaces a failure to load districts", async () => {
  server.use(
    http.get(api("/clubs/"), () => HttpResponse.json([])),
    http.get(api("/districts/"), () =>
      HttpResponse.json({ detail: "districts unavailable" }, { status: 500 }),
    ),
  );
  renderApp("/admin/clubs");
  expect(await screen.findByRole("alert")).toHaveTextContent("districts unavailable");
});
