import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function startOfRange(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days + 1);
  return date.toISOString().slice(0, 10);
}

export function moneylessNumber(value: unknown, fallback = "0") {
  if (value === null || value === undefined || value === "") return fallback;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return String(value);
  return parsed.toLocaleString("ru-RU", { maximumFractionDigits: 1 });
}
