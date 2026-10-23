import {describe, expect, it} from "vitest";
import {resolveApiBase} from "../../src/api/base";

describe("API deployment destination", () => {
  it("uses the site's API in production and the local API in development", () => {
    expect(resolveApiBase(undefined, true)).toBe("/api/v1");
    expect(resolveApiBase(undefined, false)).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveApiBase("  ", true)).toBe("/api/v1");
  });
  it("respects the explicitly selected shared server in either mode", () => {
    for (const production of [true, false]) {
      expect(resolveApiBase(" https://study.example.com/api/v1/// ", production)).toBe("https://study.example.com/api/v1");
      expect(resolveApiBase("/api/v1/", production)).toBe("/api/v1");
    }
  });
});
