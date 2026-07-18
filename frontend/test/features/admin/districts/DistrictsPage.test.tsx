import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { makeDistrict } from "../../../fixtures";
import { api, server } from "../../../msw/server";
import { renderApp } from "../../../utils";

test("lists districts", async () => {
  server.use(
    http.get(api("/districts/"), () =>
      HttpResponse.json([
        makeDistrict({ id: 1, name: "Western Cape", abbreviation: "WC" }),
        makeDistrict({ id: 2, name: "Gauteng", abbreviation: "GAU" }),
      ]),
    ),
  );
  renderApp("/admin/districts");
  expect(await screen.findByText("Western Cape")).toBeInTheDocument();
  expect(screen.getByText("GAU")).toBeInTheDocument();
});

test("shows an empty message when there are no districts", async () => {
  server.use(http.get(api("/districts/"), () => HttpResponse.json([])));
  renderApp("/admin/districts");
  expect(await screen.findByText("No districts yet.")).toBeInTheDocument();
});

test("surfaces a list error", async () => {
  server.use(
    http.get(api("/districts/"), () =>
      HttpResponse.json({ detail: "Database unavailable" }, { status: 500 }),
    ),
  );
  renderApp("/admin/districts");
  expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
});
