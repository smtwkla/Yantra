import { describe, expect, it } from "vitest";
import { isCameraName, isHeicFile, withoutExtension } from "../src/utils/documentTypes.js";

describe("isCameraName (S064 UX-11)", () => {
  it.each(["IMG_2034.jpg", "PXL_20261020_143512.jpg", "image.jpg", "20261020_143512.jpg", "DSC01234.JPG", "img-0042.png"])(
    "%s is a camera's name",
    (name) => expect(isCameraName(name)).toBe(true),
  );

  it.each(["Pump manual.pdf", "motor-nameplate.jpg", "Imagery report.pdf", "Gearbox 2026.pdf"])(
    "%s is a title",
    (name) => expect(isCameraName(name)).toBe(false),
  );
});

describe("isHeicFile", () => {
  it("knows an iPhone photo by its extension or its type", () => {
    expect(isHeicFile({ name: "IMG_1.HEIC", type: "" })).toBe(true);
    expect(isHeicFile({ name: "photo", type: "image/heif" })).toBe(true);
    expect(isHeicFile({ name: "IMG_1.jpg", type: "image/jpeg" })).toBe(false);
    expect(isHeicFile(null)).toBe(false);
  });
});

describe("withoutExtension", () => {
  it("drops the last extension only", () => {
    expect(withoutExtension("IMG_2034.jpg")).toBe("IMG_2034");
    expect(withoutExtension(".hidden")).toBe(".hidden");
  });
});
