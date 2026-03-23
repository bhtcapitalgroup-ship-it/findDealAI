import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
import { tenantsApi } from '../lib/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import DataTable, { type Column } from '../components/DataTable';

interface Tenant {
  id: string; name: string; unit: string; property: string; rent: number;
  paymentStatus: 'current' | 'late' | 'overdue' | 'partial' | 'past_due'; phone: string; email: string; leaseEnd: string;
}

const mockTenants: Tenant[] = [
  { id: '1', name: 'Sarah Johnson', unit: '1A', property: 'Maple Street Apartments', rent: 1200, paymentStatus: 'current', phone: '(503) 555-0142', email: 'sarah.j@email.com', leaseEnd: '2026-08-31' },
  { id: '2', name: 'Mike Chen', unit: '1B', property: 'Maple Street Apartments', rent: 1200, paymentStatus: 'current', phone: '(503) 555-0198', email: 'mike.c@email.com', leaseEnd: '2026-06-30' },
  { id: '3', name: 'Lisa Park', unit: '2A', property: 'Maple Street Apartments', rent: 1800, paymentStatus: 'current', phone: '(503) 555-0267', email: 'lisa.p@email.com', leaseEnd: '2026-12-31' },
  { id: '4', name: 'James Smith', unit: '3A', property: 'Maple Street Apartments', rent: 2400, paymentStatus: 'current', phone: '(503) 555-0334', email: 'james.s@email.com', leaseEnd: '2027-02-28' },
  { id: '5', name: 'Emma Wilson', unit: '3B', property: 'Maple Street Apartments', rent: 1800, paymentStatus: 'past_due', phone: '(503) 555-0411', email: 'emma.w@email.com', leaseEnd: '2026-09-30' },
  { id: '6', name: 'David Kim', unit: '4A', property: 'Maple Street Apartments', rent: 2000, paymentStatus: 'current', phone: '(503) 555-0488', email: 'david.k@email.com', leaseEnd: '2026-04-30' },
  { id: '7', name: 'Amy Taylor', unit: '4B', property: 'Maple Street Apartments', rent: 1400, paymentStatus: 'partial', phone: '(503) 555-0556', email: 'amy.t@email.com', leaseEnd: '2026-11-30' },
  { id: '8', name: 'Robert Garcia', unit: '5A', property: 'Maple Street Apartments', rent: 1800, paymentStatus: 'current', phone: '(503) 555-0623', email: 'robert.g@email.com', leaseEnd: '2026-07-31' },
  { id: '9', name: 'Nina Patel', unit: '5B', property: 'Maple Street Apartments', rent: 1400, paymentStatus: 'current', phone: '(503) 555-0691', email: 'nina.p@email.com', leaseEnd: '2027-01-31' },
  { id: '10', name: 'Carlos Rivera', unit: '6A', property: 'Maple Street Apartments', rent: 2400, paymentStatus: 'current', phone: '(503) 555-0768', email: 'carlos.r@email.com', leaseEnd: '2026-10-31' },
  { id: '11', name: 'Jennifer Lee', unit: '6C', property: 'Maple Street Apartments', rent: 1800, paymentStatus: 'current', phone: '(503) 555-0835', email: 'jennifer.l@email.com', leaseEnd: '2026-05-31' },
  { id: '12', name: 'Marcus Johnson', unit: '1A', property: 'Oak Park Townhomes', rent: 1600, paymentStatus: 'current', phone: '(503) 555-0902', email: 'marcus.j@email.com', leaseEnd: '2026-09-30' },
  { id: '13', name: 'Priya Sharma', unit: '1B', property: 'Oak Park Townhomes', rent: 1600, paymentStatus: 'past_due', phone: '(503) 555-0979', email: 'priya.s@email.com', leaseEnd: '2026-08-31' },
  { id: '14', name: 'Tom Nguyen', unit: '2A', property: 'Oak Park Townhomes', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1046', email: 'tom.n@email.com', leaseEnd: '2027-01-31' },
  { id: '15', name: 'Rachel Adams', unit: '2B', property: 'Oak Park Townhomes', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1113', email: 'rachel.a@email.com', leaseEnd: '2026-11-30' },
  { id: '16', name: 'Kevin O\'Brien', unit: '3B', property: 'Oak Park Townhomes', rent: 1600, paymentStatus: 'current', phone: '(503) 555-1180', email: 'kevin.o@email.com', leaseEnd: '2026-07-31' },
  { id: '17', name: 'Angela Martinez', unit: '4A', property: 'Oak Park Townhomes', rent: 1600, paymentStatus: 'current', phone: '(503) 555-1247', email: 'angela.m@email.com', leaseEnd: '2026-12-31' },
  { id: '18', name: 'Daniel Foster', unit: '4B', property: 'Oak Park Townhomes', rent: 1800, paymentStatus: 'partial', phone: '(503) 555-1314', email: 'daniel.f@email.com', leaseEnd: '2026-06-30' },
  { id: '19', name: 'Maria Garcia', unit: 'A', property: 'Cedar Heights Condo', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1381', email: 'maria.g@email.com', leaseEnd: '2026-10-31' },
  { id: '20', name: 'Steven Wright', unit: 'B', property: 'Cedar Heights Condo', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1448', email: 'steven.w@email.com', leaseEnd: '2027-03-31' },
  { id: '21', name: 'Laura Chen', unit: 'C', property: 'Cedar Heights Condo', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1515', email: 'laura.c@email.com', leaseEnd: '2026-09-30' },
  { id: '22', name: 'Brian Thompson', unit: 'D', property: 'Cedar Heights Condo', rent: 1800, paymentStatus: 'current', phone: '(503) 555-1582', email: 'brian.t@email.com', leaseEnd: '2026-11-30' },
];

const paymentVariant: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
  current: { label: 'Current', variant: 'success' }, late: { label: 'Late', variant: 'warning' },
  past_due: { label: 'Past Due', variant: 'danger' }, overdue: { label: 'Overdue', variant: 'danger' }, partial: { label: 'Partial', variant: 'info' },
};

export default function Tenants() {
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState('');

  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: async () => {
      const data = await tenantsApi.list();
      if (Array.isArray(data) && data.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return (data as any[]).map((t: any): Tenant => ({
          id: String(t.id),
          name: `${t.first_name || ''} ${t.last_name || ''}`.trim() || String(t.name || ''),
          unit: String(t.unit || t.unit_number || ''),
          property: String(t.property || t.property_name || ''),
          rent: Number(t.rent || t.monthly_rent || 0),
          paymentStatus: (String(t.paymentStatus || t.payment_status || 'current') as Tenant['paymentStatus']),
          phone: String(t.phone || ''),
          email: String(t.email || ''),
          leaseEnd: String(t.leaseEnd || t.lease_end || ''),
        }));
      }
      return mockTenants;
    },
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
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Property</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Maple Street Apartments</option><option>Oak Park Townhomes</option><option>Cedar Heights Condo</option></select></div>
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
