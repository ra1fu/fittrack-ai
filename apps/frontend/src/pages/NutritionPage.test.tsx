import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NutritionPage } from "./NutritionPage";

describe("NutritionPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/nutrition/days/")) {
        return new Response(JSON.stringify({ data: { date: "2026-06-19", totals: { calories: "0", protein: "0", fat: "0", carbs: "0" }, progress: {}, meals: [] }, meta: {} }));
      }
      return new Response(JSON.stringify({ data: [], meta: { count: 0, total_count: 0, limit: 10, offset: 0 } }));
    }));
  });

  it("renders nutrition totals", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <NutritionPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Nutrition")).toBeInTheDocument();
    expect(await screen.findByText("Калории")).toBeInTheDocument();
  });
});
