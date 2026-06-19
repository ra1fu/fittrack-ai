import {
  forwardRef,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "../lib/utils";

export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="grid gap-1 text-sm font-medium text-ink">
      <span>{label}</span>
      {children}
      {error ? <span className="text-xs font-medium text-coral">{error}</span> : null}
    </label>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  props,
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "min-h-11 rounded-md border border-line bg-white px-3 py-2 text-base text-ink shadow-[inset_0_1px_0_rgba(23,33,29,0.03)] placeholder:text-muted/70 transition hover:border-[#c9c4b8]",
        props.className,
      )}
      {...props}
    />
  );
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  props,
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "min-h-11 rounded-md border border-line bg-white px-3 py-2 text-base text-ink shadow-[inset_0_1px_0_rgba(23,33,29,0.03)] transition hover:border-[#c9c4b8]",
        props.className,
      )}
      {...props}
    />
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea(props, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "min-h-24 rounded-md border border-line bg-white px-3 py-2 text-base text-ink shadow-[inset_0_1px_0_rgba(23,33,29,0.03)] transition hover:border-[#c9c4b8]",
        props.className,
      )}
      {...props}
    />
  );
});
