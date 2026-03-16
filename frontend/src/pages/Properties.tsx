import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Building2, MapPin, Home, DollarSign } from 'lucide-react';
import api from '../lib/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const mockProperties = [
  { id: '1', name: 'Oak Manor Apartments', address: '142 Oak Street, Portland, OR 97201', type: 'Multi-Family', units: 8, occupied: 7, monthlyIncome: 14400 },
  { id: '2', name: 'Elm Street Duplex', address: '89 Elm Street, Portland, OR 97205', type: 'Duplex', units: 2, occupied: 2, monthlyIncome: 3800 },
  { id: '3', name: 'Pine Ridge Townhomes', address: '567 Pine Ridge Dr, Beaverton, OR 97008', type: 'Townhome', units: 6, occupied: 5, monthlyIncome: 13200 },
  { id: '4', name: 'Cedar Heights', address: '234 Cedar Blvd, Lake Oswego, OR 97034', type: 'Multi-Family', units: 4, occupied: 4, monthlyIncome: 8800 },
  { id: '5', name: 'Maple View SFR', address: '91 Maple Ave, Tigard, OR 97223', type: 'Single Family', units: 1, occupied: 1, monthlyIncome: 2200 },
  { id: '6', name: 'Birch Park Complex', address: '410 Birch Park Ln, Hillsboro, OR 97124', type: 'Multi-Family', units: 3, occupied: 3, monthlyIncome: 5100 },
];

export default function Properties() {
  const navigate = useNavigate();
  const [showAdd, setShowAdd] = useState(false);

  const { data: properties } = useQuery({
    queryKey: ['properties'],
    queryFn: async () => { const res = await api.get('/properties'); return res.data; },
    placeholderData: mockProperties,
  });

  const list = properties ?? mockProperties;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Properties</h1>
          <p className="text-sm text-zinc-500 mt-1">{list.length} properties in your portfolio</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
          <Plus className="w-4 h-4" />Add Property
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {list.map((p: typeof mockProperties[0]) => {
          const occupancy = Math.round((p.occupied / p.units) * 100);
          return (
            <div key={p.id} onClick={() => navigate(`/properties/${p.id}`)} className="bg-white rounded-xl border border-zinc-200 shadow-sm hover:shadow-md hover:border-zinc-300 transition-all cursor-pointer overflow-hidden group">
              <div className="h-36 bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center relative overflow-hidden">
                <Building2 className="w-12 h-12 text-slate-300" />
                <div className="absolute top-3 right-3">
                  <Badge variant={occupancy === 100 ? 'success' : occupancy >= 75 ? 'info' : 'warning'}>{occupancy}% occupied</Badge>
                </div>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <h3 className="font-semibold text-zinc-900 group-hover:text-blue-600 transition-colors">{p.name}</h3>
                  <div className="flex items-center gap-1 mt-1 text-sm text-zinc-500"><MapPin className="w-3.5 h-3.5" />{p.address}</div>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-zinc-100">
                  <div className="flex items-center gap-1 text-sm text-zinc-600"><Home className="w-3.5 h-3.5" />{p.units} unit{p.units !== 1 ? 's' : ''}</div>
                  <div className="flex items-center gap-1 text-sm font-semibold text-zinc-900"><DollarSign className="w-3.5 h-3.5 text-emerald-500" />{p.monthlyIncome.toLocaleString()}/mo</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Property" size="lg">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setShowAdd(false); }}>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Property Name</label>
            <input type="text" placeholder="e.g. Oak Manor Apartments" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Address</label>
            <input type="text" placeholder="Street address" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Property Type</label>
              <select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Multi-Family</option><option>Single Family</option><option>Duplex</option><option>Townhome</option></select>
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Number of Units</label>
              <input type="number" min={1} placeholder="1" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Add Property</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
