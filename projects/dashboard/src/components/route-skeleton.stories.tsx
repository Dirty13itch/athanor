import type { Meta, StoryObj } from "@storybook/react";
import { RouteSkeleton } from "@/components/route-skeleton";

const meta = {
  title: "Feedback/RouteSkeleton",
  component: RouteSkeleton,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof RouteSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    blocks: 4,
    tall: false,
  },
};

export const Tall: Story = {
  args: {
    blocks: 4,
    tall: true,
  },
};
