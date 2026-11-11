// @vitest-environment node
import { describe, expect, it } from "vitest";
import { appVersion } from "./version";

describe("appVersion", () => {
  it("prend APP_VERSION quand la CI la fournit", () => {
    expect(appVersion({ APP_VERSION: " v1.2.3 " })).toBe("v1.2.3");
  });

  it("sinon : version de package.json + date du build UTC", () => {
    expect(appVersion({}, new Date("2026-11-11T14:32:09Z"))).toMatch(
      /^\d+\.\d+\.\d+\+20261111\.1432$/,
    );
  });
});
