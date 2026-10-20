"use client";

import { Fragment, type ReactNode } from "react";

type Block =
  | { kind: "heading"; level: 2 | 3 | 4; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "quote"; text: string }
  | { kind: "code"; text: string }
  | { kind: "divider" };

const HEADING_PATTERN = /^(#{1,4})\s+(.*)$/;
const UNORDERED_PATTERN = /^\s*[-*•]\s+(.*)$/;
const ORDERED_PATTERN = /^\s*\d+[.)]\s+(.*)$/;
const QUOTE_PATTERN = /^\s*>\s?(.*)$/;
const FENCE_PATTERN = /^\s*```/;
const INLINE_PATTERN = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)/g;

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let quote: string[] = [];
  let code: string[] | null = null;

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", text: paragraph.join("\n") });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list) {
      blocks.push({ kind: "list", ordered: list.ordered, items: list.items });
      list = null;
    }
  };
  const flushQuote = () => {
    if (quote.length > 0) {
      blocks.push({ kind: "quote", text: quote.join("\n") });
      quote = [];
    }
  };
  const flushAll = () => {
    flushParagraph();
    flushList();
    flushQuote();
  };

  for (const line of lines) {
    if (code) {
      if (FENCE_PATTERN.test(line)) {
        blocks.push({ kind: "code", text: code.join("\n") });
        code = null;
      } else {
        code.push(line);
      }
      continue;
    }
    if (FENCE_PATTERN.test(line)) {
      flushAll();
      code = [];
      continue;
    }
    if (line.trim() === "") {
      flushAll();
      continue;
    }
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      flushAll();
      blocks.push({ kind: "divider" });
      continue;
    }
    const heading = HEADING_PATTERN.exec(line);
    if (heading) {
      flushAll();
      const level = Math.min(4, Math.max(2, heading[1].length)) as 2 | 3 | 4;
      blocks.push({ kind: "heading", level, text: heading[2].trim() });
      continue;
    }
    const quoteMatch = QUOTE_PATTERN.exec(line);
    if (quoteMatch) {
      flushParagraph();
      flushList();
      quote.push(quoteMatch[1]);
      continue;
    }
    const unordered = UNORDERED_PATTERN.exec(line);
    const ordered = ORDERED_PATTERN.exec(line);
    if (unordered || ordered) {
      flushParagraph();
      flushQuote();
      const item = (unordered ?? ordered)![1];
      if (!list || list.ordered !== Boolean(ordered)) {
        flushList();
        list = { ordered: Boolean(ordered), items: [] };
      }
      list.items.push(item);
      continue;
    }
    flushList();
    flushQuote();
    paragraph.push(line);
  }

  if (code) {
    blocks.push({ kind: "code", text: code.join("\n") });
  }
  flushAll();
  return blocks;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(INLINE_PATTERN).map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (!part) return null;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={key} className="italic">
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={key}
          className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] text-slate-700"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <Fragment key={key}>{part}</Fragment>;
  });
}

const HEADING_CLASSES: Record<2 | 3 | 4, string> = {
  2: "text-lg font-bold text-slate-900",
  3: "text-base font-bold text-slate-900",
  4: "text-sm font-bold text-slate-800",
};

export function RichText({ content }: { content: string }) {
  const blocks = parseBlocks(content);

  return (
    <div className="space-y-2">
      {blocks.map((block, index) => {
        const key = `b-${index}`;
        if (block.kind === "heading") {
          const Tag = `h${block.level}` as "h2" | "h3" | "h4";
          return (
            <Tag
              key={key}
              className={`text-balance ${HEADING_CLASSES[block.level]}`}
            >
              {renderInline(block.text, key)}
            </Tag>
          );
        }
        if (block.kind === "list") {
          const items = block.items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`} className="text-pretty">
              {renderInline(item, `${key}-${itemIndex}`)}
            </li>
          ));
          return block.ordered ? (
            <ol key={key} className="list-decimal space-y-1 ps-5 marker:text-slate-400">
              {items}
            </ol>
          ) : (
            <ul key={key} className="list-disc space-y-1 ps-5 marker:text-slate-400">
              {items}
            </ul>
          );
        }
        if (block.kind === "quote") {
          return (
            <blockquote
              key={key}
              className="border-s-2 border-emerald-200 ps-3 text-slate-600"
            >
              {renderInline(block.text, key)}
            </blockquote>
          );
        }
        if (block.kind === "code") {
          return (
            <pre
              key={key}
              className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs leading-6 text-slate-100"
            >
              <code>{block.text}</code>
            </pre>
          );
        }
        if (block.kind === "divider") {
          return <hr key={key} className="border-slate-200" />;
        }
        return (
          <p key={key} className="text-pretty whitespace-pre-wrap">
            {renderInline(block.text, key)}
          </p>
        );
      })}
    </div>
  );
}
