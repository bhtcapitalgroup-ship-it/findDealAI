import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
import api from '../lib/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import DataTable, { type Column } from '../components/DataTable';

interface Tenant {
  id: string; name: string; unit: string; property: string; rent: number;
  paymentStatus: 'current' | 'late' | 'overdue' | 'partial'; phone: string; email: string; leaseEnd: string;
}

const mockTenants: Tenant[] = [
  { id: '1', name: 'Sarah Johnson', unit: '1A', property: 'Oak Manor', rent: 1800, paymentStatus: 'current', phone: '(503) 555-0142', email: 'sarah.j@email.com', leaseEnd: '2026-08-31' },
  { id: '2', name: 'Mike Chen', unit: '1B', property: 'Oak Manor', rent: 1400, paymentStatus: 'late', phone: '(503) 555-0198', email: 'mike.c@email.com', leaseEnd: '2026-06-30' },
  { id: '3', name: 'Lisa Park', unit: '2A', property: 'Oak Manor', rent: 1850, paymentStatus: 'current', phone: '(503) 555-0267', email: 'lisa.p@email.com', leaseEnd: '2026-12-31' },
  { id: '4', name: 'David Kim', unit: '3A', property: 'Oak Manor', rent: 2400, paymentStatus: 'current', phone: '(503) 555-0334', email: 'david.k@email.com', leaseEnd: '2027-02-28' },
  { id: '5', name: 'Emma Wilson', unit: '3B', property: 'Oak Manor', rent: 1850, paymentStatus: 'overdue', phone: '(503) 555-0411', email: 'emma.w@email.com', leaseEnd: '2026-09-30' },
  { id: '6', name: 'James Brown', unit: '4A', property: 'Oak Manor', rent: 2000, paymentStatus: 'current', phone: '(503) 555-0488', email: 'james.b@email.com', leaseEnd: '2026-04-30' },
  { id: '7', name: 'Amy Taylor', unit: '4B', property: 'Oak Manor', rent: 1700, paymentStatus: 'partial', phone: '(503) 555-0556', email: 'amy.t@email.com', leaseEnd: '2026-11-30' },
  { id: '8', name: 'Robert Garcia', unit: 'A', property: 'Elm Street Duplex', rent: 1900, paymentStatus: 'current', phone: '(503) 555-0623', email: 'robert.g@email.com', leaseEnd: '2026-07-31' },
  { id: '9', name: 'Nina Patel', unit: 'B', property: 'Elm Street Duplex', rent: 1900, paymentStatus: 'current', phone: '(503) 555-0691', email: 'nina.p@email.com', leaseEnd: '2027-01-31' },
  { id: '10', name: 'Carlos Rivera', unit: '1', property: 'Pine Ridge Townhomes', rent: 2200, paymentStatus: 'current', phone: '(503) 555-0768', email: 'carlos.r@email.com', leaseEnd: '2026-10-31' },
];

const paymentVariant: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
  current: { label: 'Current', variant: 'success' }, late: { label: 'Late', variant: 'warning' },
  overdue: { label: 'Overdue', variant: 'danger' }, partial: { label: 'Partial', variant: 'info' },
};

export default function Tenants() {
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState('');

  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: async () => { const res = await api.get('/tenants'); return res.data; },
    placeholderData: mockTenants,
  });

  const list: Tenant[] = tenants ?? mockTenants;
  const filtered = list.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()) || t.property.toLowerCase().includes(search.toLowerCase()) || t.unit.toLowerCase().includes(search.toLowerCase()));

  const columns: Column<Tenant>[] = [
    { key: 'name', label: 'Tenant', sortable: true, render: (row) => (<div><div className="font-semibold text-zinc-900">{row.name}</div><div className="text-xs text-zinc-500">{row.email}</div></div>) },
    { key: 'unit', label: 'Unit', sortable: true },
    { key: 'property', label: 'Property', sortable: true },
    { key: 'rent', label: 'Rent', sortable: true, render: (row) => `$${row.rent.toLocaleString()}` },
    { key: 'paymentStatus', label: 'Payment Status', sortable: true, render: (row) => { const s = paymentVariant[row.paymentStatus]; return <Badge variant={s.variant} dot>{s.label}</Badge>; } },
    { key: 'phone', label: 'Phone' },
    { key: 'leaseEnd', label: 'Lease Ends', sortable: true },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-zinc-900">Tenants</h1><p className="text-sm text-zinc-500 mt-1">{list.length} active tenants</p></div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"><Plus className="w-4 h-4" />Add Tenant</button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search tenants..." className="w-full pl-10 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
        </div>
      </div>

      <DataTable columns={columns} data={filtered} keyExtractor={(t) => t.id} />

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Tenant" size="lg">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setShowAdd(false); }}>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Full Name</label><input type="text" placeholder="John Doe" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Email</label><input type="email" placeholder="john@email.com" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Phone</label><input type="tel" placeholder="(503) 555-0000" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Monthly Rent</label><input type="number" min={0} placeholder="1800" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Property</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Oak Manor Apartments</option><option>Elm Street Duplex</option><option>Pine Ridge Townhomes</option></select></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Unit</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>2B (Vacant)</option></select></div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Add Tenant</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
