"use client";

import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function ScoreBadge({ score, size = "md", showLabel = false, className }: ScoreBadgeProps) {
  const circumference = 2 * Math.PI * 18;
  const progress = (score / 100) * circumference;
  const offset = circumference - progress;

  const color = score >= 80 ? "#059669" : score >= 60 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";
  const label = score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Fair" : "Poor";

  const sizeClasses = { sm: "w-10 h-10", md: "w-14 h-14", lg: "w-20 h-20" };
  const fontSizes = { sm: "text-[10px]", md: "text-sm", lg: "text-xl" };

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <div className={cn("relative", sizeClasses[size])}>
        <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="none" stroke="#1f2937" strokeWidth="3" />
          <circle cx="20" cy="20" r="18" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className="transition-all duration-700 ease-out" />
        </svg>
        <div className={cn("absolute inset-0 flex items-center justify-center font-bold", fontSizes[size])} style={{ color }}>{score}</div>
      </div>
      {showLabel && <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color }}>{label}</span>}
    </div>
  );
}
