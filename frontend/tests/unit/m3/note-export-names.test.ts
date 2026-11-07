import {expect, it} from "vitest";
import {markdownFilename} from "../../../src/features/notes/exportNames";

it("uses readable titles and handles Windows filename constraints", () => {
  expect(markdownFilename("进程与线程")).toBe("进程与线程.md");
  expect(markdownFilename("../概念:步骤? ")).toBe("_概念_步骤_.md");
  expect(markdownFilename("CON.txt")).toBe("_CON.txt.md");
  expect(markdownFilename("ＣＯＭ１")).toBe("_COM1.md");
  expect(markdownFilename("... \n\0")).toBe("未命名笔记.md");
  expect(new TextEncoder().encode(markdownFilename("😀".repeat(100))).length).toBeLessThanOrEqual(223);
});
