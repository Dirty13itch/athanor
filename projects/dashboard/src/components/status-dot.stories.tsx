import type { Meta, StoryObj } from "@storybook/react";
import { StatusDot } from "@/components/status-dot";

const meta = {
  title: "Data/StatusDot",
  component: StatusDot,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof StatusDot>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Healthy: Story = {
  args: {
    tone: "healthy",
  },
};

export const WarningPulse: Story = {
  args: {
    tone: "warning",
    pulse: true,
  },
};

export const Danger: Story = {
  args: {
    tone: "danger",
  },
};
