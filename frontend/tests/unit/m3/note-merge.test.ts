import {describe, expect, it} from "vitest";
import {MERGE_LIMITS, mergeField, mergeText, resolveText, type ReadyMergePlan} from "../../../src/features/notes/noteMerge";

function ready(base: string, local: string, server: string): ReadyMergePlan {
  const result = mergeText(base, local, server);
  expect(result.kind).toBe("ready");
  if (result.kind !== "ready") throw new Error(result.reason);
  return result;
}
const text = (plan: ReadyMergePlan) => resolveText(plan, {});
const choose = (plan: ReadyMergePlan, side: "local" | "server") => resolveText(plan,
  Object.fromEntries(plan.segments.filter(segment => segment.kind === "conflict").map(segment => [segment.id, side])));
const numbered = (count: number, prefix = "原文") => Array.from({length: count}, (_, index) => `${prefix} ${index}\n`);

describe("笔记逐段三方合并", () => {
  it("保留未改内容，合并两侧不相邻的修改", () => {
    const plan = ready("标题\n甲\n乙\n丙\n", "标题\n本地甲\n乙\n丙\n", "标题\n甲\n乙\n服务端丙\n");
    expect(plan.conflictCount).toBe(0);
    expect(text(plan)).toBe("标题\n本地甲\n乙\n服务端丙\n");
    expect(plan.comparedCells).toBeGreaterThan(0);
  });
  it("相邻非空行修改仍可独立合并", () => {
    expect(text(ready("甲\n乙\n丙\n", "一\n乙\n丙\n", "甲\n二\n丙\n"))).toBe("一\n二\n丙\n");
  });
  it("组合多处增删并保留双方相同的修改一份", () => {
    const plan = ready("a\nb\nc\nd\ne\nf\n", "A\nb\nc\nd\nf\n", "A\nb\nnew\nc\nd\ne\nf\n");
    expect(plan.conflictCount).toBe(0);
    expect(text(plan)).toBe("A\nb\nnew\nc\nd\nf\n");
  });
  it("同一位置同样插入去重，不同插入要求选择", () => {
    const identical = ready("a\nb\nc\nd\n", "a\nnew\nb\nc\nd\n", "a\nnew\nb\nc\nD\n");
    expect(text(identical)).toBe("a\nnew\nb\nc\nD\n");
    const conflict = ready("a\nb\n", "a\n本地插入\nb\n", "a\n服务端插入\nb\n");
    expect(conflict.conflictCount).toBe(1);
    expect(conflict.segments[1]).toMatchObject({kind: "conflict", base: "", startLine: 2, endLine: 2});
    expect(choose(conflict, "local")).toBe("a\n本地插入\nb\n");
    expect(choose(conflict, "server")).toBe("a\n服务端插入\nb\n");
  });
  it("删除与重写同段必须核对，保留完整的基线与双方段落", () => {
    const plan = ready("a\nb\nc\nd\ne\n", "a\nd\ne\n", "a\nb\n改写c\nd\n改写e\n");
    expect(plan.conflictCount).toBe(1);
    expect(plan.segments[1]).toMatchObject({kind: "conflict", base: "b\nc\n", local: "", server: "b\n改写c\n", startLine: 2, endLine: 3});
    expect(choose(plan, "local")).toBe("a\nd\n改写e\n");
    expect(choose(plan, "server")).toBe("a\nb\n改写c\nd\n改写e\n");
  });
  it("跨多个修改的重叠区段合并为一项明确冲突", () => {
    const plan = ready("a\nb\nc\nd\ne\nf\n", "a\nB\nc\nD\ne\nf\n", "a\n整个段落\nf\n");
    expect(plan.conflictCount).toBe(1);
    expect(choose(plan, "local")).toBe("a\nB\nc\nD\ne\nf\n");
    expect(choose(plan, "server")).toBe("a\n整个段落\nf\n");
  });
  it("两个分离冲突必须各自选择，无选择时不返回部分结果", () => {
    const plan = ready("a\nb\nc\nd\ne\n", "a\n本地b\nc\n本地d\ne\n", "a\n远端b\nc\n远端d\ne\n");
    expect(plan.conflictCount).toBe(2);
    expect(text(plan)).toBeNull();
    expect(resolveText(plan, {"conflict-1": "local"})).toBeNull();
    expect(resolveText(plan, {"conflict-1": "local", "conflict-2": "server"})).toBe("a\n本地b\nc\n远端d\ne\n");
  });
  it("删除边界上的插入保守地交由用户选择", () => {
    for (const local of ["a\n插入\nb\nc\n", "a\nb\n插入\nc\n"]) {
      const plan = ready("a\nb\nc\n", local, "a\nc\n");
      expect(plan.conflictCount).toBe(1);
      expect(choose(plan, "local")).toBe(local);
      expect(choose(plan, "server")).toBe("a\nc\n");
    }
  });
  it("保留 CRLF、独立 CR、空行、Unicode、公式和未换行结尾的原始字节", () => {
    const base = "# 标题😀\r\n\r\n$x^2$\r旧行\n[链接](note:uuid)";
    const local = base.replace("标题😀", "标题😀修改");
    const server = base.replace("旧行", "新行");
    expect(text(ready(base, local, server))).toBe(local.replace("旧行", "新行"));
    expect(text(ready("a\nb", "A\nb", "a\nb\n"))).toBe("A\nb\n");
  });
  it("重复行不会被省略或多次生成", () => {
    const plan = ready("a\nx\nx\nb\nx\nx\nc\n", "a\nx\nb\nx\nx\nc\n", "a\nx\nx\nb\nx\nx\nC\n");
    expect(text(plan)).toBe("a\nx\nb\nx\nx\nC\n");
  });
  it("空基线、全删和开头末尾插入保持完整", () => {
    expect(text(ready("", "新文档", ""))).toBe("新文档");
    const empty = ready("", "本地", "远端");
    expect(empty.conflictCount).toBe(1);
    expect(choose(empty, "local")).toBe("本地");
    expect(text(ready("a\n", "", "a\n"))).toBe("");
    expect(text(ready("a\nb\n", "前\na\nb\n", "a\nb\n后"))).toBe("前\na\nb\n后");
  });
  it("Markdown 和 HTML 只是字符串，不生成冲突标记或转义正文", () => {
    const local = "<script>alert('x')</script>\n尾行\n";
    const server = "起始\n![图](assets/图.png)\n";
    const result = text(ready("起始\n尾行\n", local, server));
    expect(result).toBe("<script>alert('x')</script>\n![图](assets/图.png)\n");
    expect(result).not.toContain("<<<<<<<");
  });
  it("缺少共同版本时明确退回手动核对", () => {
    expect(mergeText(null, "本地", "远端")).toMatchObject({kind: "unavailable", reason: expect.stringContaining("共同版本")});
  });
});

describe("输入与算法预算", () => {
  it("字符与行预算即使双方相同也先检查，不静默截断", () => {
    const tooLong = "a".repeat(MERGE_LIMITS.characters + 1);
    expect(mergeText(tooLong, tooLong, tooLong)).toMatchObject({kind: "unavailable", reason: expect.stringContaining("200,000")});
    const tooMany = "a\n".repeat(MERGE_LIMITS.lines + 1);
    expect(mergeText("", tooMany, "")).toMatchObject({kind: "unavailable", reason: expect.stringContaining("10,000")});
    const exact = "a".repeat(MERGE_LIMITS.characters);
    expect(text(ready(exact, exact, exact))).toBe(exact);
    const exactLines = "a\n".repeat(MERGE_LIMITS.lines);
    expect(text(ready(exactLines, exactLines, exactLines))).toBe(exactLines);
  });
  it("前后公共内容不消耗二次矩阵预算", () => {
    const source = numbered(9_999), local = [...source], server = [...source];
    local[3] = "本地修改\n"; server[9_990] = "服务端修改\n";
    const plan = ready(source.join(""), local.join(""), server.join(""));
    expect(plan.comparedCells).toBe(8);
    local[9_990] = server[9_990];
    expect(text(plan)).toBe(local.join(""));
  });
  it("两次比较共享单元预算，不能每次单独放行", () => {
    const result = mergeText(numbered(1_000).join(""), numbered(1_000, "本地").join(""), numbered(1_000, "服务端").join(""));
    expect(result).toMatchObject({kind: "unavailable", reason: expect.stringContaining("2,000,000")});
  });
  it("对全部不同的大文档在分配大矩阵前拒绝", () => {
    const result = mergeText(numbered(9_000).join(""), numbered(9_000, "本地").join(""), numbered(9_000, "服务端").join(""));
    expect(result.kind).toBe("unavailable");
  });
  it("允许预算内的完整对比，记录实际分配的比较单元", () => {
    const plan = ready(numbered(900).join(""), numbered(900, "本地").join(""), numbered(900, "服务端").join(""));
    expect(plan.comparedCells).toBe(2 * 901 * 901);
    expect(plan.conflictCount).toBe(1);
    expect(choose(plan, "local")).toBe(numbered(900, "本地").join(""));
  });
});

describe("可重复的多样本不变量", () => {
  let seed = 0x6d33001;
  const random = () => {seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 0x100000000;};
  it("250 组互不重叠行编辑同时保留，并满足交换两侧结果不变", () => {
    for (let iteration = 0; iteration < 250; iteration++) {
      const count = 5 + Math.floor(random() * 35), base = numbered(count);
      const local = [...base], server = [...base], expected = [...base];
      for (let index = 0; index < count; index++) {
        const owner = Math.floor(random() * 3);
        if (owner === 1) local[index] = expected[index] = `本地 ${iteration} ${index}\n`;
        if (owner === 2) server[index] = expected[index] = `服务端 ${iteration} ${index}\n`;
      }
      const plan = ready(base.join(""), local.join(""), server.join(""));
      expect(plan.conflictCount).toBe(0);
      expect(text(plan)).toBe(expected.join(""));
      expect(text(ready(base.join(""), server.join(""), local.join("")))).toBe(expected.join(""));
    }
  });
  it("150 组不确定重叠可对称地选择双方，单侧及同改恒等式保留全部文本", () => {
    for (let iteration = 0; iteration < 150; iteration++) {
      const parts = Array.from({length: 12}, () => ["x\n", "y\r\n", "😀\r", "\n"][Math.floor(random() * 4)]);
      const base = parts.join(""), localParts = [...parts], serverParts = [...parts];
      localParts.splice(Math.floor(random() * 12), Math.floor(random() * 4), `本地 ${iteration}\n`);
      serverParts.splice(Math.floor(random() * 12), Math.floor(random() * 4), `服务端 ${iteration}\n`);
      const local = localParts.join(""), server = serverParts.join("");
      expect(text(ready(base, local, base))).toBe(local);
      expect(text(ready(base, base, server))).toBe(server);
      expect(text(ready(base, local, local))).toBe(local);
      const direct = ready(base, local, server), swapped = ready(base, server, local);
      expect(choose(direct, "local")).toBe(choose(swapped, "server"));
      expect(choose(direct, "server")).toBe(choose(swapped, "local"));
    }
  });
});

describe("标题、标签和文件夹字段核对", () => {
  it("采用唯一改动和相同改动，保留空值", () => {
    expect(mergeField("原题", "原题", "新题")).toEqual({conflict: false, value: "新题"});
    expect(mergeField("原题", "本地", "原题")).toEqual({conflict: false, value: "本地"});
    expect(mergeField<string | null>("folder-1", null, "folder-1")).toEqual({conflict: false, value: null});
    expect(mergeField(["旧"], ["共同"], ["共同"])).toEqual({conflict: false, value: ["共同"]});
  });
  it("两侧独立改标签或文件夹时不静默取并集或选择覆盖", () => {
    expect(mergeField(["旧"], ["旧", "甲"], ["旧", "乙"])).toEqual({conflict: true, value: ["旧", "甲"]});
    expect(mergeField<string | null>(null, "folder-a", "folder-b").conflict).toBe(true);
    expect(mergeField(["甲", "乙"], ["乙", "甲"], ["丙"]).conflict).toBe(true);
  });
  it("JSON 对象按字段深比较且不修改输入", () => {
    const base = {name: "旧", nested: {tags: ["一"]}}, local = {nested: {tags: ["一"]}, name: "旧"};
    const server = {name: "新", nested: {tags: ["二"]}};
    expect(mergeField(base, local, server)).toEqual({conflict: false, value: server});
    expect(base).toEqual({name: "旧", nested: {tags: ["一"]}});
  });
});
