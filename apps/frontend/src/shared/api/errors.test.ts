import { describe, expect, it } from "vitest";
import { parseApiError } from "./errors";

describe("parseApiError", () => {
  it("reads backend error envelope", () => {
    const error = parseApiError(400, {
      error: {
        code: "VALIDATION_ERROR",
        message: "Проверьте поля",
        fields: { email: "Некорректный email" },
        request_id: "req_1",
      },
    });

    expect(error.message).toBe("Проверьте поля");
    expect(error.fields.email).toBe("Некорректный email");
    expect(error.requestId).toBe("req_1");
  });
});
