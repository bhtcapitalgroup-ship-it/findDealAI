"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import type { ColumnDef } from "@/types";

interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
  compact?: boolean;
}

export function DataTable<T extends Record<string, unknown>>({ columns, data, onRowClick, emptyMessage = "No data available", className, compact = false }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const handleSort = useCallback((key: string) => {
    if (sortKey === key) { setSortOrder((o) => (o === "asc" ? "desc" : "asc")); }
    else { setSortKey(key); setSortOrder("asc"); }
  }, [sortKey]);

  const sortedData = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = a[sortKey]; const bVal = b[sortKey];
    if (aVal == null || bVal == null) return 0;
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortOrder === "asc" ? cmp : -cmp;
  });

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-brand-border">
            {columns.map((col) => (
              <th key={String(col.key)} className={cn("text-left font-medium text-brand-muted uppercase tracking-wider", compact ? "px-3 py-2 text-[10px]" : "px-4 py-3 text-xs", col.align === "right" && "text-right", col.align === "center" && "text-center", col.sortable && "cursor-pointer select-none hover:text-gray-300")} style={{ width: col.width }} onClick={() => col.sortable && handleSort(String(col.key))}>
                <div className={cn("flex items-center gap-1", col.align === "right" && "justify-end", col.align === "center" && "justify-center")}>
                  {col.header}
                  {col.sortable && (<span className="inline-flex">{sortKey === String(col.key) ? (sortOrder === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />) : <ChevronsUpDown className="w-3 h-3 opacity-30" />}</span>)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.length === 0 ? (
            <tr><td colSpan={columns.length} className="text-center text-brand-muted py-12">{emptyMessage}</td></tr>
          ) : (
            sortedData.map((row, i) => (
              <tr key={i} className={cn("border-b border-brand-border/50 transition-colors", onRowClick && "cursor-pointer hover:bg-brand-surface")} onClick={() => onRowClick?.(row)}>
                {columns.map((col) => (
                  <td key={String(col.key)} className={cn(compact ? "px-3 py-2" : "px-4 py-3", col.align === "right" && "text-right", col.align === "center" && "text-center")}>
                    {col.render ? col.render(row[String(col.key)], row) : String(row[String(col.key)] ?? "-")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
