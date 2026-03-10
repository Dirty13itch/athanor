import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { ROUTES } from "@/lib/navigation";
import { RouteIcon } from "@/components/route-icon";

const meta = {
  title: "Navigation/RouteIcon",
  component: RouteIcon,
  parameters: {
    layout: "centered",
  },
} satisfies Meta<typeof RouteIcon>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Gallery: Story = {
  args: {
    icon: "dashboard",
  },
  render: () => (
    <div className="grid grid-cols-3 gap-4 rounded-2xl border border-border/70 bg-background p-6 text-sm sm:grid-cols-4 lg:grid-cols-6">
      {ROUTES.map((route) => (
        <div
          key={route.href}
          className="flex flex-col items-center gap-2 rounded-xl border border-border/60 bg-card/60 p-3 text-center"
        >
          <RouteIcon icon={route.icon} className="h-5 w-5 text-primary" />
          <span>{route.shortLabel ?? route.label}</span>
        </div>
      ))}
    </div>
  ),
};
