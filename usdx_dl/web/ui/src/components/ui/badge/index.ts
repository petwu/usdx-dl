import type { VariantProps } from "class-variance-authority"
import { cva } from "class-variance-authority"

export { default as Badge } from "./Badge.vue"

export const badgeVariants = cva(
  "focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive inline-flex w-fit shrink-0 items-center justify-center gap-1 border px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:ring-[3px] [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        "default":
          "bg-primary text-primary-foreground hover:bg-primary/80 border-transparent",
        "secondary":
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 border-transparent",
        "success":
          "bg-success hover:bg-success/80 focus-visible:ring-success/20 dark:focus-visible:ring-success/40 dark:bg-success/60 text-success-foreground border-transparent",
        "warning":
          "bg-warning hover:bg-warning/80 focus-visible:ring-warning/20 dark:focus-visible:ring-warning/40 dark:bg-warning/60 text-warning-foreground border-transparent",
        "destructive":
          "bg-destructive hover:bg-destructive/80 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60 text-destructive-foreground border-transparent",
        "destructive-outline":
          "border-destructive hover:bg-destructive/10 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60 text-destructive",
        "muted": "bg-muted text-muted-foreground hover:bg-muted/80 border-transparent",
        "outline": "text-foreground hover:bg-accent hover:text-accent-foreground",
      },
      pill: {
        true: "rounded-full",
        false: "rounded-sm",
      },
      size: {
        xs: "px-1 py-0.25 text-xs leading-none [&>svg]:size-3",
        sm: "text-sm [&>svg]:size-3.5",
        md: "text-base [&>svg]:size-4",
        lg: "text-lg [&>svg]:size-4.5",
        xl: "text-xl [&>svg]:size-5",
      },
    },
    defaultVariants: {
      variant: "default",
      pill: false,
      size: "xs",
    },
  },
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
