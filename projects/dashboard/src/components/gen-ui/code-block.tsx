"use client";

import { useState } from "react";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="relative my-2 rounded-md border border-border bg-muted">
      <div className="flex items-center justify-between px-3 py-1 border-b border-border">
        {language && (
          <span className="text-[10px] font-mono text-muted-foreground uppercase">{language}</span>
        )}
        {!language && <span />}
        <button
          onClick={handleCopy}
          className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 max-h-64 text-xs font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
