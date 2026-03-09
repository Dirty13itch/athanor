import type { Meta, StoryObj } from "@storybook/react";
import { Activity } from "lucide-react";
import { StatCard } from "@/components/stat-card";

const meta = {
  title: "Data/StatCard",
  component: StatCard,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof StatCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Healthy: Story = {
  args: {
    label: "Cluster health",
    value: "14/14",
    detail: "All monitored endpoints are reachable.",
    tone: "success",
    icon: <Activity className="h-5 w-5" />,
  },
};
