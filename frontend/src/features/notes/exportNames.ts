/** Portable title names, matching the server's single-note download header. */
export function markdownFilename(title: string): string {
  let value = title.normalize("NFKC").replace(/\p{C}/gu, "").replace(/[<>:"/\\|?*]/g, "_").replace(/\s+/g, " ").replace(/^[ .]+|[ .]+$/g, "");
  value = Array.from(value).slice(0, 60).join("");
  const encoder = new TextEncoder();
  while (encoder.encode(value).length > 220) value = Array.from(value).slice(0, -1).join("");
  value = value.replace(/[ .]+$/g, "") || "未命名笔记";
  if (/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i.test(value.split(".")[0])) value = "_" + value;
  return value + ".md";
}
