import type { Meta, StoryObj } from "@storybook/react";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";

const meta = {
  title: "Feedback/EmptyState",
  component: EmptyState,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: "No sessions yet",
    description: "Create a new session to begin testing a model or agent workflow.",
    icon: <Bot className="h-5 w-5" />,
    action: <Button>New session</Button>,
  },
};
