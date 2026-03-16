import { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import clsx from 'clsx';

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  keyExtractor: (row: T) => string;
}

export default function DataTable<T>({ columns, data, onRowClick, keyExtractor }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const sortedData = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = (a as Record<string, unknown>)[sortKey];
    const bVal = (b as Record<string, unknown>)[sortKey];
    if (aVal == null || bVal == null) return 0;
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function handleSort(key: string) {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50/50">
            {columns.map((col) => (
              <th key={col.key} className={clsx('px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider', col.sortable && 'cursor-pointer select-none hover:text-zinc-700', col.className)} onClick={() => col.sortable && handleSort(col.key)}>
                <div className="flex items-center gap-1">
                  {col.label}
                  {col.sortable && (
                    <span className="text-zinc-300">
                      {sortKey === col.key ? (sortDir === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />) : <ChevronsUpDown className="w-3.5 h-3.5" />}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row) => (
            <tr key={keyExtractor(row)} className={clsx('border-b border-zinc-100 last:border-0 transition-colors', onRowClick && 'cursor-pointer hover:bg-zinc-50')} onClick={() => onRowClick?.(row)}>
              {columns.map((col) => (
                <td key={col.key} className={clsx('px-4 py-3 text-zinc-700', col.className)}>
                  {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
          {sortedData.length === 0 && (
            <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-zinc-400">No data found</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
