import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatCompact(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: "text-emerald-400",
    occupied: "text-emerald-400",
    completed: "text-emerald-400",
    current: "text-emerald-400",
    vacant: "text-amber-400",
    pending: "text-amber-400",
    routine: "text-blue-400",
    urgent: "text-amber-400",
    emergency: "text-red-400",
    past_due: "text-red-400",
    failed: "text-red-400",
    expired: "text-zinc-400",
    maintenance: "text-orange-400",
    turnover: "text-purple-400",
  };
  return colors[status] || "text-zinc-400";
}

export function getUrgencyBg(urgency: string): string {
  const colors: Record<string, string> = {
    emergency: "bg-red-500/10 border-red-500/30 text-red-400",
    urgent: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    routine: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  };
  return colors[urgency] || "bg-zinc-500/10 border-zinc-500/30 text-zinc-400";
}
