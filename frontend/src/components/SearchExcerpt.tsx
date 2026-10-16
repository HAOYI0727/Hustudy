import { Fragment } from "react";
import type { TextExcerpt } from "../api/client";

/** Offsets from the API count Unicode characters, including supplementary planes. */
export function SearchExcerpt({ excerpt }: { excerpt: TextExcerpt }) {
  const characters = Array.from(excerpt.text);
  let cursor = 0;
  const content = excerpt.highlights.map((span, index) => {
    const start = Math.max(cursor, Math.min(characters.length, span.start));
    const end = Math.max(start, Math.min(characters.length, span.end));
    const before = characters.slice(cursor, start).join("");
    const hit = characters.slice(start, end).join("");
    cursor = end;
    return <Fragment key={index}>{before}<mark>{hit}</mark></Fragment>;
  });
  return <>{excerpt.start_offset > 0 && "…"}{content}{characters.slice(cursor).join("")}{excerpt.truncated_after && "…"}</>;
}
