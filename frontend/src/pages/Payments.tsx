import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DollarSign, Clock, AlertCircle, TrendingUp, Plus } from 'lucide-react';
import api from '../lib/api';
import StatCard from '../components/StatCard';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import DataTable, { type Column } from '../components/DataTable';

interface Payment {
  id: string; tenant: string; unit: string; amount: number; dueDate: string; paidDate: string | null;
  status: 'paid' | 'pending' | 'late' | 'overdue'; method: string;
}

const mockPayments: Payment[] = [
  { id: '1', tenant: 'Sarah Johnson', unit: '1A - Oak Manor', amount: 1800, dueDate: '2026-03-01', paidDate: '2026-02-28', status: 'paid', method: 'ACH' },
  { id: '2', tenant: 'Mike Chen', unit: '1B - Oak Manor', amount: 1400, dueDate: '2026-03-01', paidDate: null, status: 'late', method: '--' },
  { id: '3', tenant: 'Lisa Park', unit: '2A - Oak Manor', amount: 1850, dueDate: '2026-03-01', paidDate: '2026-03-01', status: 'paid', method: 'Credit Card' },
  { id: '4', tenant: 'David Kim', unit: '3A - Oak Manor', amount: 2400, dueDate: '2026-03-01', paidDate: '2026-03-02', status: 'paid', method: 'ACH' },
  { id: '5', tenant: 'Emma Wilson', unit: '3B - Oak Manor', amount: 1850, dueDate: '2026-03-01', paidDate: null, status: 'overdue', method: '--' },
  { id: '6', tenant: 'James Brown', unit: '4A - Oak Manor', amount: 2000, dueDate: '2026-03-01', paidDate: '2026-03-01', status: 'paid', method: 'ACH' },
  { id: '7', tenant: 'Amy Taylor', unit: '4B - Oak Manor', amount: 1700, dueDate: '2026-03-01', paidDate: null, status: 'pending', method: '--' },
  { id: '8', tenant: 'Robert Garcia', unit: 'A - Elm Street', amount: 1900, dueDate: '2026-03-01', paidDate: '2026-02-27', status: 'paid', method: 'Check' },
  { id: '9', tenant: 'Nina Patel', unit: 'B - Elm Street', amount: 1900, dueDate: '2026-03-01', paidDate: '2026-03-03', status: 'paid', method: 'ACH' },
  { id: '10', tenant: 'Carlos Rivera', unit: '1 - Pine Ridge', amount: 2200, dueDate: '2026-03-01', paidDate: '2026-03-01', status: 'paid', method: 'ACH' },
];

const statusVariant: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
  paid: { label: 'Paid', variant: 'success' }, pending: { label: 'Pending', variant: 'info' },
  late: { label: 'Late', variant: 'warning' }, overdue: { label: 'Overdue', variant: 'danger' },
};

export default function Payments() {
  const [showRecord, setShowRecord] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: payments } = useQuery({
    queryKey: ['payments'],
    queryFn: async () => { const res = await api.get('/payments'); return res.data; },
    placeholderData: mockPayments,
  });

  const list: Payment[] = payments ?? mockPayments;
  const filtered = statusFilter === 'all' ? list : list.filter((p) => p.status === statusFilter);
  const collected = list.filter((p) => p.status === 'paid').reduce((s, p) => s + p.amount, 0);
  const outstanding = list.filter((p) => p.status !== 'paid').reduce((s, p) => s + p.amount, 0);
  const lateCount = list.filter((p) => p.status === 'late' || p.status === 'overdue').length;
  const total = list.reduce((s, p) => s + p.amount, 0);
  const collectionRate = Math.round((collected / total) * 100);

  const columns: Column<Payment>[] = [
    { key: 'tenant', label: 'Tenant', sortable: true, render: (row) => <span className="font-semibold text-zinc-900">{row.tenant}</span> },
    { key: 'unit', label: 'Unit', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (row) => `$${row.amount.toLocaleString()}` },
    { key: 'dueDate', label: 'Due Date', sortable: true },
    { key: 'paidDate', label: 'Paid Date', sortable: true, render: (row) => row.paidDate || <span className="text-zinc-400">--</span> },
    { key: 'status', label: 'Status', sortable: true, render: (row) => { const s = statusVariant[row.status]; return <Badge variant={s.variant} dot>{s.label}</Badge>; } },
    { key: 'method', label: 'Method' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-zinc-900">Payments</h1><p className="text-sm text-zinc-500 mt-1">March 2026 collection overview</p></div>
        <button onClick={() => setShowRecord(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"><Plus className="w-4 h-4" />Record Payment</button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Collected" value={`$${collected.toLocaleString()}`} icon={DollarSign} />
        <StatCard label="Outstanding" value={`$${outstanding.toLocaleString()}`} icon={AlertCircle} />
        <StatCard label="Late Payments" value={String(lateCount)} icon={Clock} />
        <StatCard label="Collection Rate" value={`${collectionRate}%`} icon={TrendingUp} />
      </div>

      <div className="flex items-center gap-2">
        {['all', 'paid', 'pending', 'late', 'overdue'].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)} className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-colors ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'}`}>{s.charAt(0).toUpperCase() + s.slice(1)}</button>
        ))}
      </div>

      <DataTable columns={columns} data={filtered} keyExtractor={(p) => p.id} />

      <Modal open={showRecord} onClose={() => setShowRecord(false)} title="Record Payment">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setShowRecord(false); }}>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Tenant</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">{list.filter((p) => p.status !== 'paid').map((p) => (<option key={p.id}>{p.tenant} - {p.unit}</option>))}</select></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Amount</label><input type="number" min={0} placeholder="1800" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Method</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>ACH</option><option>Credit Card</option><option>Check</option><option>Cash</option></select></div>
          </div>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Date Paid</label><input type="date" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowRecord(false)} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Record</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
