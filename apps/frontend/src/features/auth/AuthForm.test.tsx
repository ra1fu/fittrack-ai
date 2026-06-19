import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthForm } from "./AuthForm";

function renderForm() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthForm mode="login" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AuthForm", () => {
  it("keeps submit disabled until fields are valid", async () => {
    renderForm();
    const submit = screen.getByRole("button", { name: /войти/i });
    expect(submit).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
    await userEvent.type(screen.getByLabelText(/пароль/i), "password123");

    await waitFor(() => expect(submit).toBeEnabled());
  });
});
