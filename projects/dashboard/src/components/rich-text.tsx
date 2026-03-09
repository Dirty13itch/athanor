import { Fragment } from "react";

function renderInline(text: string) {
  return text.split(/(`[^`]+`)/g).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={index} className="rounded bg-black/20 px-1.5 py-0.5 font-mono text-[0.92em]">
          {part.slice(1, -1)}
        </code>
      );
    }

    return <Fragment key={index}>{part}</Fragment>;
  });
}

export function RichText({ content }: { content: string }) {
  const blocks = content.split(/```/g);

  return (
    <div className="space-y-3 leading-6">
      {blocks.map((block, index) => {
        if (index % 2 === 1) {
          const lines = block.split("\n");
          const language = lines[0]?.trim();
          const code = lines.slice(1).join("\n").trim();
          return (
            <pre
              key={index}
              className="overflow-x-auto rounded-2xl border border-border/70 bg-black/25 p-4 font-mono text-xs text-foreground"
            >
              {language ? <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{language}</p> : null}
              <code>{code}</code>
            </pre>
          );
        }

        return block
          .split(/\n{2,}/g)
          .filter(Boolean)
          .map((paragraph, paragraphIndex) => (
            <p key={`${index}-${paragraphIndex}`} className="text-sm whitespace-pre-wrap">
              {renderInline(paragraph)}
            </p>
          ));
      })}
    </div>
  );
}
