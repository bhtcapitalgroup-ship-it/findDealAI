import { type LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trend?: { value: string; positive: boolean };
  className?: string;
}

export default function StatCard({ label, value, icon: Icon, trend, className }: StatCardProps) {
  return (
    <div className={clsx('bg-white rounded-xl border border-zinc-200 p-5 shadow-sm hover:shadow-md transition-shadow', className)}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
          <Icon className="w-[18px] h-[18px] text-blue-600" />
        </div>
      </div>
      <div className="text-2xl font-bold text-zinc-900">{value}</div>
      {trend && (
        <div className="mt-1.5 flex items-center gap-1">
          <span className={clsx('text-xs font-semibold', trend.positive ? 'text-emerald-600' : 'text-red-500')}>
            {trend.positive ? '+' : ''}{trend.value}
          </span>
          <span className="text-xs text-zinc-400">vs last month</span>
        </div>
      )}
    </div>
  );
}
