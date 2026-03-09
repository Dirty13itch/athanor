import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";

const meta = {
  title: "Layout/PageHeader",
  component: PageHeader,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof PageHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    eyebrow: "Operations",
    title: "Command Center",
    description: "Cluster posture, alerts, and launch paths for the Athanor operator.",
    actions: (
      <>
        <Button variant="outline">Open incidents</Button>
        <Button>Resume agents</Button>
      </>
    ),
  },
};
