"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, LucideIcon } from "lucide-react";

interface MetricCardProps {
  icon?: LucideIcon;
  label: string;
  value: string | number;
  trend?: { value: number; isPositive: boolean };
  subtitle?: string;
  className?: string;
  valueClassName?: string;
}

export function MetricCard({ icon: Icon, label, value, trend, subtitle, className, valueClassName }: MetricCardProps) {
  return (
    <div className={cn("card p-4 flex flex-col gap-2 animate-fade-in", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-brand-muted" />}
      </div>
      <div className="flex items-end gap-2">
        <span className={cn("text-2xl font-bold tracking-tight text-white", valueClassName)}>{value}</span>
        {trend && (
          <span className={cn("flex items-center gap-0.5 text-xs font-medium mb-1", trend.isPositive ? "text-profit" : "text-loss")}>
            {trend.isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {Math.abs(trend.value).toFixed(1)}%
          </span>
        )}
      </div>
      {subtitle && <span className="text-xs text-brand-muted">{subtitle}</span>}
    </div>
  );
}
