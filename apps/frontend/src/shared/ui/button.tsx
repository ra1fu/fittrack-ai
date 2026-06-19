import { ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  isLoading?: boolean;
};

export function Button({ className, variant = "primary", isLoading, children, disabled, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-bold transition duration-150 active:translate-y-px disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-55",
        variant === "primary" && "bg-action text-white shadow-soft hover:bg-[#116744]",
        variant === "secondary" && "border border-line bg-white text-ink shadow-[0_1px_0_rgba(23,33,29,0.04)] hover:border-[#cac6bb] hover:bg-[#f6f3ec]",
        variant === "danger" && "bg-coral text-white shadow-soft hover:bg-[#bd4f36]",
        variant === "ghost" && "text-ink hover:bg-[#ebe7dc]",
        className,
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Загрузка...
        </>
      ) : (
        children
      )}
    </button>
  );
}
