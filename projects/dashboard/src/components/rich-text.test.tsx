import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RichText } from "@/components/rich-text";

describe("RichText", () => {
  it("renders paragraphs, inline code, and fenced code blocks", () => {
    render(
      <RichText
        content={`Hello \`world\`\n\n\`\`\`ts\nconst answer = 42;\n\`\`\``}
      />
    );

    expect(screen.getByText("world")).toBeInTheDocument();
    expect(screen.getByText("const answer = 42;")).toBeInTheDocument();
  });
});
