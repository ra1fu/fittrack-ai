import { HTMLAttributes } from "react";
import { cn } from "../lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-lg border border-line/80 bg-panel/95 p-4 shadow-soft ring-1 ring-white/70",
        className,
      )}
      {...props}
    />
  );
}
