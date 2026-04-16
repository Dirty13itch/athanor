import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[0.8rem] text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/40 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default:
          "border border-primary/30 bg-primary/12 text-foreground shadow-none hover:bg-primary/18",
        destructive:
          "border border-destructive/40 bg-destructive/16 text-white hover:bg-destructive/22 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40",
        outline:
          "border border-border/80 bg-transparent shadow-none hover:bg-accent hover:text-accent-foreground dark:bg-transparent dark:border-border/80 dark:hover:bg-accent/80",
        secondary:
          "border border-border/60 bg-secondary text-secondary-foreground hover:bg-secondary/90",
        ghost:
          "hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/80",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        xs: "h-6 gap-1 rounded-[0.65rem] px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 rounded-[0.7rem] gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-[0.9rem] px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-xs": "size-6 rounded-[0.65rem] [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8 rounded-[0.7rem]",
        "icon-lg": "size-10 rounded-[0.9rem]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
