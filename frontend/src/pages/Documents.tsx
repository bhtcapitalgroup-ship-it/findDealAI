import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Upload, LayoutGrid, List, Search, Bot, Download, Eye, Filter } from 'lucide-react';
import clsx from 'clsx';
import api from '../lib/api';
import Badge from '../components/Badge';

interface Document { id: string; name: string; type: 'lease' | 'inspection' | 'contract' | 'receipt' | 'other'; property: string; uploadedAt: string; size: string; status: 'active' | 'expired' | 'pending'; }

const mockDocuments: Document[] = [
  { id: '1', name: 'Lease Agreement - Sarah Johnson', type: 'lease', property: 'Oak Manor', uploadedAt: '2026-01-15', size: '2.4 MB', status: 'active' },
  { id: '2', name: 'Lease Agreement - Mike Chen', type: 'lease', property: 'Oak Manor', uploadedAt: '2025-12-01', size: '2.1 MB', status: 'active' },
  { id: '3', name: 'Annual Inspection Report 2025', type: 'inspection', property: 'Oak Manor', uploadedAt: '2025-11-20', size: '5.7 MB', status: 'active' },
  { id: '4', name: 'Plumbing Repair Contract', type: 'contract', property: 'Elm Street Duplex', uploadedAt: '2026-02-10', size: '890 KB', status: 'active' },
  { id: '5', name: 'HVAC Maintenance Receipt', type: 'receipt', property: 'Pine Ridge', uploadedAt: '2026-03-05', size: '340 KB', status: 'active' },
  { id: '6', name: 'Lease Agreement - David Kim', type: 'lease', property: 'Oak Manor', uploadedAt: '2025-09-01', size: '2.3 MB', status: 'active' },
  { id: '7', name: 'Lease Agreement - Former Tenant', type: 'lease', property: 'Oak Manor', uploadedAt: '2024-03-15', size: '1.9 MB', status: 'expired' },
  { id: '8', name: 'Fire Inspection Certificate', type: 'inspection', property: 'All Properties', uploadedAt: '2026-01-30', size: '1.2 MB', status: 'active' },
  { id: '9', name: 'Landscaping Contract Q1 2026', type: 'contract', property: 'Pine Ridge', uploadedAt: '2026-01-05', size: '650 KB', status: 'active' },
  { id: '10', name: 'Appliance Purchase Receipt', type: 'receipt', property: 'Elm Street Duplex', uploadedAt: '2026-02-22', size: '180 KB', status: 'active' },
];

const typeColors: Record<string, { label: string; variant: 'info' | 'success' | 'purple' | 'warning' | 'neutral' }> = {
  lease: { label: 'Lease', variant: 'info' }, inspection: { label: 'Inspection', variant: 'success' },
  contract: { label: 'Contract', variant: 'purple' }, receipt: { label: 'Receipt', variant: 'warning' }, other: { label: 'Other', variant: 'neutral' },
};

export default function Documents() {
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [dragOver, setDragOver] = useState(false);

  const { data: documents } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => { const res = await api.get('/documents'); return res.data; },
    placeholderData: mockDocuments,
  });

  const list: Document[] = documents ?? mockDocuments;
  const filtered = list.filter((d) => d.name.toLowerCase().includes(search.toLowerCase()) && (typeFilter === 'all' || d.type === typeFilter));

  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setDragOver(false); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-zinc-900">Documents</h1><p className="text-sm text-zinc-500 mt-1">{list.length} documents</p></div>
        <label className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm cursor-pointer"><Upload className="w-4 h-4" />Upload<input type="file" className="hidden" multiple /></label>
      </div>

      <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
        className={clsx('border-2 border-dashed rounded-xl p-8 text-center transition-colors', dragOver ? 'border-blue-400 bg-blue-50' : 'border-zinc-200 bg-white hover:border-zinc-300')}>
        <Upload className="w-8 h-8 text-zinc-300 mx-auto mb-2" />
        <p className="text-sm text-zinc-600 font-medium">Drag and drop files here, or <label className="text-blue-600 hover:text-blue-700 cursor-pointer font-semibold">browse<input type="file" className="hidden" multiple /></label></p>
        <p className="text-xs text-zinc-400 mt-1">PDF, DOC, JPG, PNG up to 25MB</p>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" /><input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents..." className="w-full pl-10 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
        <div className="flex items-center gap-2"><Filter className="w-4 h-4 text-zinc-400" />{['all', 'lease', 'inspection', 'contract', 'receipt'].map((t) => (<button key={t} onClick={() => setTypeFilter(t)} className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-colors ${typeFilter === t ? 'bg-blue-600 text-white' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'}`}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>))}</div>
        <div className="flex items-center gap-1 ml-auto">
          <button onClick={() => setView('grid')} className={clsx('p-2 rounded-lg transition-colors', view === 'grid' ? 'bg-zinc-200 text-zinc-800' : 'text-zinc-400 hover:text-zinc-600')}><LayoutGrid className="w-4 h-4" /></button>
          <button onClick={() => setView('list')} className={clsx('p-2 rounded-lg transition-colors', view === 'list' ? 'bg-zinc-200 text-zinc-800' : 'text-zinc-400 hover:text-zinc-600')}><List className="w-4 h-4" /></button>
        </div>
      </div>

      {view === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((doc) => { const tc = typeColors[doc.type]; return (
            <div key={doc.id} className="bg-white rounded-xl border border-zinc-200 shadow-sm hover:shadow-md hover:border-zinc-300 transition-all p-4 group">
              <div className="w-12 h-12 rounded-lg bg-zinc-100 flex items-center justify-center mb-3"><FileText className="w-6 h-6 text-zinc-400" /></div>
              <h3 className="text-sm font-semibold text-zinc-900 line-clamp-2 mb-2">{doc.name}</h3>
              <div className="flex items-center gap-2 mb-2"><Badge variant={tc.variant}>{tc.label}</Badge>{doc.status === 'expired' && <Badge variant="danger">Expired</Badge>}</div>
              <div className="text-xs text-zinc-500 space-y-0.5"><p>{doc.property}</p><p>{doc.uploadedAt} &middot; {doc.size}</p></div>
              <div className="flex items-center gap-1 mt-3 pt-3 border-t border-zinc-100 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 rounded text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"><Eye className="w-4 h-4" /></button>
                <button className="p-1.5 rounded text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"><Download className="w-4 h-4" /></button>
                {doc.type === 'lease' && <button className="ml-auto flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-purple-600 hover:bg-purple-50 transition-colors"><Bot className="w-3.5 h-3.5" />Analyze</button>}
              </div>
            </div>
          ); })}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-zinc-200 divide-y divide-zinc-100">
          {filtered.map((doc) => { const tc = typeColors[doc.type]; return (
            <div key={doc.id} className="flex items-center gap-4 px-4 py-3 hover:bg-zinc-50 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0"><FileText className="w-5 h-5 text-zinc-400" /></div>
              <div className="flex-1 min-w-0"><p className="text-sm font-semibold text-zinc-900 truncate">{doc.name}</p><p className="text-xs text-zinc-500">{doc.property} &middot; {doc.uploadedAt}</p></div>
              <Badge variant={tc.variant}>{tc.label}</Badge>
              <span className="text-xs text-zinc-400 w-16 text-right">{doc.size}</span>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"><Eye className="w-4 h-4" /></button>
                <button className="p-1.5 rounded text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"><Download className="w-4 h-4" /></button>
                {doc.type === 'lease' && <button className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-purple-600 hover:bg-purple-50 transition-colors"><Bot className="w-3.5 h-3.5" />Analyze</button>}
              </div>
            </div>
          ); })}
        </div>
      )}
    </div>
  );
}
