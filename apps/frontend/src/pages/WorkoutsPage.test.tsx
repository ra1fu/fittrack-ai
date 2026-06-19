import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkoutsPage } from "./WorkoutsPage";

describe("WorkoutsPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/workouts/active")) return new Response(JSON.stringify({ data: null, meta: {} }));
      return new Response(JSON.stringify({ data: [], meta: { count: 0, total_count: 0, limit: 50, offset: 0 } }));
    }));
  });

  it("renders start workout form", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <WorkoutsPage />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Старт тренировки")).toBeInTheDocument();
  });
});
