import type { Meta, StoryObj } from "@storybook/react";
import { ErrorPanel } from "@/components/error-panel";

const meta = {
  title: "Feedback/ErrorPanel",
  component: ErrorPanel,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof ErrorPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: "Service history unavailable",
    description:
      "Prometheus did not return the expected blackbox metrics for the selected window.",
  },
};
