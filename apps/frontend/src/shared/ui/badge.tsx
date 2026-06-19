import { HTMLAttributes } from "react";
import { cn } from "../lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "dark";

const toneClass: Record<BadgeTone, string> = {
  neutral: "bg-oat text-steel",
  success: "bg-mint text-action",
  warning: "bg-[#f2e5ce] text-amber",
  danger: "bg-[#f4dfd6] text-coral",
  dark: "bg-ink text-white",
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center rounded-md px-2.5 py-1 text-xs font-black uppercase tracking-normal",
        toneClass[tone],
        className,
      )}
      {...props}
    />
  );
}
