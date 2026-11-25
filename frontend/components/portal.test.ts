import { describe, expect, it } from "vitest";

describe("Frontend unit tests", () => {
  it("formats file sizes correctly", () => {
    const bytes = (value: number) =>
      value < 1024 * 1024
        ? `${Math.round(value / 1024)} KB`
        : `${(value / 1024 / 1024).toFixed(1)} MB`;

    expect(bytes(500)).toBe("0 KB");
    expect(bytes(2048)).toBe("2 KB");
    expect(bytes(1048576)).toBe("1.0 MB");
    expect(bytes(5242880)).toBe("5.0 MB");
  });

  it("replaces underscores in badges", () => {
    const formatBadge = (val: string) => val.replaceAll("_", " ");
    expect(formatBadge("MISSING_INFORMATION")).toBe("MISSING INFORMATION");
    expect(formatBadge("IMPORTANT_CLAUSE")).toBe("IMPORTANT CLAUSE");
  });
});
