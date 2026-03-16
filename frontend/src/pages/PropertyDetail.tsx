import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, DollarSign, TrendingUp, ArrowLeft, Plus } from 'lucide-react';
import api from '../lib/api';
import StatCard from '../components/StatCard';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import DataTable, { type Column } from '../components/DataTable';

interface Unit {
  id: string; number: string; bedrooms: number; bathrooms: number; sqft: number; rent: number;
  status: 'occupied' | 'vacant' | 'maintenance' | 'notice'; tenant: string | null;
}

const mockProperty = {
  id: '1', name: 'Oak Manor Apartments', address: '142 Oak Street, Portland, OR 97201', type: 'Multi-Family',
  monthlyIncome: 14400, monthlyExpenses: 5200, noi: 9200,
  units: [
    { id: 'u1', number: '1A', bedrooms: 2, bathrooms: 1, sqft: 850, rent: 1800, status: 'occupied' as const, tenant: 'Sarah Johnson' },
    { id: 'u2', number: '1B', bedrooms: 1, bathrooms: 1, sqft: 650, rent: 1400, status: 'occupied' as const, tenant: 'Mike Chen' },
    { id: 'u3', number: '2A', bedrooms: 2, bathrooms: 1, sqft: 850, rent: 1850, status: 'occupied' as const, tenant: 'Lisa Park' },
    { id: 'u4', number: '2B', bedrooms: 1, bathrooms: 1, sqft: 650, rent: 1400, status: 'vacant' as const, tenant: null },
    { id: 'u5', number: '3A', bedrooms: 3, bathrooms: 2, sqft: 1100, rent: 2400, status: 'occupied' as const, tenant: 'David Kim' },
    { id: 'u6', number: '3B', bedrooms: 2, bathrooms: 1, sqft: 850, rent: 1850, status: 'occupied' as const, tenant: 'Emma Wilson' },
    { id: 'u7', number: '4A', bedrooms: 2, bathrooms: 2, sqft: 950, rent: 2000, status: 'notice' as const, tenant: 'James Brown' },
    { id: 'u8', number: '4B', bedrooms: 1, bathrooms: 1, sqft: 650, rent: 1700, status: 'occupied' as const, tenant: 'Amy Taylor' },
  ],
};

const statusBadge: Record<string, { label: string; variant: 'success' | 'danger' | 'warning' | 'info' }> = {
  occupied: { label: 'Occupied', variant: 'success' },
  vacant: { label: 'Vacant', variant: 'danger' },
  maintenance: { label: 'Maintenance', variant: 'warning' },
  notice: { label: 'Notice Given', variant: 'info' },
};

export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [showAddUnit, setShowAddUnit] = useState(false);

  const { data: property } = useQuery({
    queryKey: ['property', id],
    queryFn: async () => { const res = await api.get(`/properties/${id}`); return res.data; },
    placeholderData: mockProperty,
  });

  const p = property ?? mockProperty;

  const columns: Column<Unit>[] = [
    { key: 'number', label: 'Unit', sortable: true, render: (row) => <span className="font-semibold text-zinc-900">{row.number}</span> },
    { key: 'bedrooms', label: 'Bed/Bath', sortable: true, render: (row) => `${row.bedrooms}bd / ${row.bathrooms}ba` },
    { key: 'sqft', label: 'Sq Ft', sortable: true, render: (row) => row.sqft.toLocaleString() },
    { key: 'rent', label: 'Rent', sortable: true, render: (row) => `$${row.rent.toLocaleString()}` },
    { key: 'status', label: 'Status', sortable: true, render: (row) => { const s = statusBadge[row.status]; return <Badge variant={s.variant} dot>{s.label}</Badge>; } },
    { key: 'tenant', label: 'Tenant', render: (row) => row.tenant || <span className="text-zinc-400 italic">--</span> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => navigate('/properties')} className="flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-700 mb-3 transition-colors"><ArrowLeft className="w-4 h-4" />Back to Properties</button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">{p.name}</h1>
            <div className="flex items-center gap-1 mt-1 text-sm text-zinc-500"><MapPin className="w-4 h-4" />{p.address}</div>
            <Badge variant="info" className="mt-2">{p.type}</Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Monthly Income" value={`$${p.monthlyIncome.toLocaleString()}`} icon={DollarSign} />
        <StatCard label="Monthly Expenses" value={`$${p.monthlyExpenses.toLocaleString()}`} icon={TrendingUp} />
        <StatCard label="Net Operating Income" value={`$${p.noi.toLocaleString()}`} icon={TrendingUp} trend={{ value: '5.2%', positive: true }} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-900">Units ({p.units.length})</h2>
          <button onClick={() => setShowAddUnit(true)} className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"><Plus className="w-4 h-4" />Add Unit</button>
        </div>
        <DataTable columns={columns} data={p.units} keyExtractor={(u: Unit) => u.id} />
      </div>

      <Modal open={showAddUnit} onClose={() => setShowAddUnit(false)} title="Add Unit">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setShowAddUnit(false); }}>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Unit Number</label><input type="text" placeholder="e.g. 5A" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Bedrooms</label><input type="number" min={0} placeholder="2" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Bathrooms</label><input type="number" min={0} placeholder="1" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Monthly Rent</label><input type="number" min={0} placeholder="1800" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowAddUnit(false)} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Add Unit</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
