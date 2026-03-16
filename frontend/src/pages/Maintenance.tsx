import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Clock, AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import api from '../lib/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

interface Ticket {
  id: string; ticketNumber: string; unit: string; property: string; category: string;
  description: string; urgency: 'emergency' | 'urgent' | 'routine'; status: 'open' | 'in_progress' | 'completed'; createdAt: string;
}

const mockTickets: Ticket[] = [
  { id: '1', ticketNumber: 'MT-1042', unit: '1B', property: 'Oak Manor', category: 'Plumbing', description: 'Kitchen sink leaking under the cabinet. Water damage visible on floor.', urgency: 'emergency', status: 'open', createdAt: '2026-03-16T10:30:00Z' },
  { id: '2', ticketNumber: 'MT-1041', unit: '3A', property: 'Oak Manor', category: 'HVAC', description: 'Heater not turning on. Temperature dropping in unit.', urgency: 'emergency', status: 'in_progress', createdAt: '2026-03-15T22:00:00Z' },
  { id: '3', ticketNumber: 'MT-1040', unit: '4A', property: 'Oak Manor', category: 'Electrical', description: 'Multiple outlets in bedroom not working. Breaker keeps tripping.', urgency: 'urgent', status: 'open', createdAt: '2026-03-15T14:00:00Z' },
  { id: '4', ticketNumber: 'MT-1039', unit: 'A', property: 'Elm Street Duplex', category: 'Appliance', description: 'Dishwasher making grinding noise and not completing cycles.', urgency: 'urgent', status: 'open', createdAt: '2026-03-15T09:00:00Z' },
  { id: '5', ticketNumber: 'MT-1038', unit: '2A', property: 'Oak Manor', category: 'General', description: 'Bathroom door handle loose. Needs tightening or replacement.', urgency: 'routine', status: 'open', createdAt: '2026-03-14T16:00:00Z' },
  { id: '6', ticketNumber: 'MT-1037', unit: '1', property: 'Pine Ridge', category: 'Exterior', description: 'Gutter detached from roofline on south side of building.', urgency: 'routine', status: 'in_progress', createdAt: '2026-03-14T11:00:00Z' },
  { id: '7', ticketNumber: 'MT-1036', unit: '3B', property: 'Oak Manor', category: 'Painting', description: 'Ceiling water stain in living room from previous plumbing repair.', urgency: 'routine', status: 'open', createdAt: '2026-03-13T09:00:00Z' },
  { id: '8', ticketNumber: 'MT-1035', unit: 'B', property: 'Elm Street Duplex', category: 'Pest Control', description: 'Ant infestation in kitchen area near window. Recurring issue.', urgency: 'routine', status: 'open', createdAt: '2026-03-12T15:00:00Z' },
];

const urgencyConfig = {
  emergency: { label: 'Emergency', color: 'bg-red-500', headerBg: 'bg-red-50', headerText: 'text-red-800', icon: AlertCircle },
  urgent: { label: 'Urgent', color: 'bg-amber-500', headerBg: 'bg-amber-50', headerText: 'text-amber-800', icon: AlertTriangle },
  routine: { label: 'Routine', color: 'bg-emerald-500', headerBg: 'bg-emerald-50', headerText: 'text-emerald-800', icon: CheckCircle2 },
};

export default function Maintenance() {
  const navigate = useNavigate();
  const [showNew, setShowNew] = useState(false);

  const { data: tickets } = useQuery({
    queryKey: ['maintenance'],
    queryFn: async () => { const res = await api.get('/maintenance'); return res.data; },
    placeholderData: mockTickets,
  });

  const list: Ticket[] = tickets ?? mockTickets;
  const cols = { emergency: list.filter((t) => t.urgency === 'emergency'), urgent: list.filter((t) => t.urgency === 'urgent'), routine: list.filter((t) => t.urgency === 'routine') };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-zinc-900">Maintenance</h1><p className="text-sm text-zinc-500 mt-1">{list.filter((t) => t.status !== 'completed').length} open requests</p></div>
        <button onClick={() => setShowNew(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"><Plus className="w-4 h-4" />New Request</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {(['emergency', 'urgent', 'routine'] as const).map((urgency) => {
          const cfg = urgencyConfig[urgency];
          const Icon = cfg.icon;
          return (
            <div key={urgency} className="space-y-3">
              <div className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg', cfg.headerBg)}>
                <Icon className={clsx('w-4 h-4', cfg.headerText)} />
                <span className={clsx('text-sm font-semibold', cfg.headerText)}>{cfg.label}</span>
                <span className={clsx('ml-auto text-xs font-bold px-2 py-0.5 rounded-full text-white', cfg.color)}>{cols[urgency].length}</span>
              </div>
              <div className="space-y-2">
                {cols[urgency].map((ticket) => (
                  <div key={ticket.id} onClick={() => navigate(`/maintenance/${ticket.id}`)} className="bg-white rounded-lg border border-zinc-200 p-4 cursor-pointer hover:shadow-md hover:border-zinc-300 transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-semibold text-zinc-500">{ticket.ticketNumber}</span>
                      <Badge variant={ticket.status === 'in_progress' ? 'info' : 'neutral'} dot>{ticket.status === 'in_progress' ? 'In Progress' : 'Open'}</Badge>
                    </div>
                    <div className="text-xs text-zinc-500 mb-1">{ticket.unit} - {ticket.property}</div>
                    <Badge variant="neutral" className="mb-2">{ticket.category}</Badge>
                    <p className="text-sm text-zinc-700 line-clamp-2 mb-3">{ticket.description}</p>
                    <div className="flex items-center gap-1 text-xs text-zinc-400"><Clock className="w-3 h-3" />{formatDistanceToNow(new Date(ticket.createdAt), { addSuffix: true })}</div>
                  </div>
                ))}
                {cols[urgency].length === 0 && <div className="text-center py-8 text-sm text-zinc-400">No {urgency} tickets</div>}
              </div>
            </div>
          );
        })}
      </div>

      <Modal open={showNew} onClose={() => setShowNew(false)} title="New Maintenance Request" size="lg">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setShowNew(false); }}>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Property</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Oak Manor Apartments</option><option>Elm Street Duplex</option><option>Pine Ridge Townhomes</option></select></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Unit</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>1A</option><option>1B</option><option>2A</option><option>2B</option></select></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Category</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Plumbing</option><option>HVAC</option><option>Electrical</option><option>Appliance</option><option>General</option></select></div>
            <div><label className="block text-sm font-medium text-zinc-700 mb-1">Urgency</label><select className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"><option>Routine</option><option>Urgent</option><option>Emergency</option></select></div>
          </div>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Description</label><textarea rows={3} placeholder="Describe the issue..." className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" /></div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowNew(false)} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Create Request</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
