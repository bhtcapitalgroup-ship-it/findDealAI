import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Bot, Camera, CheckCircle2, Clock, DollarSign, Wrench, AlertTriangle, ThumbsUp, ThumbsDown, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import api from '../lib/api';
import Badge from '../components/Badge';

const mockRequest = {
  id: '1', ticketNumber: 'MT-1042', title: 'Kitchen Sink Leak', unit: '1B', property: 'Oak Manor Apartments',
  category: 'Plumbing', urgency: 'emergency' as const, status: 'in_progress' as const,
  description: 'Kitchen sink is leaking under the cabinet. Water has pooled on the floor and there is visible damage to the cabinet base. The leak appears to be coming from the P-trap connection.',
  createdAt: '2026-03-16T10:30:00Z', tenant: 'Mike Chen', photos: [1, 2, 3],
  aiDiagnosis: {
    category: 'Plumbing - Drain/P-trap', severity: 78,
    recommendedAction: 'Replace P-trap assembly and inspect surrounding pipes for corrosion. Check for water damage to cabinet floor.',
    estimatedCost: { low: 150, high: 350 }, confidence: 92,
  },
  quotes: [
    { id: 'q1', contractor: 'Portland Plumbing Co.', amount: 280, eta: '1-2 days', status: 'pending' as const },
    { id: 'q2', contractor: 'Quick Fix Services', amount: 320, eta: 'Same day', status: 'pending' as const },
    { id: 'q3', contractor: 'A+ Home Repair', amount: 245, eta: '2-3 days', status: 'pending' as const },
  ],
  timeline: [
    { id: 't1', event: 'Request created by tenant', time: '2026-03-16T10:30:00Z', type: 'created' },
    { id: 't2', event: 'AI classified as Emergency - Plumbing', time: '2026-03-16T10:30:05Z', type: 'ai' },
    { id: 't3', event: 'AI diagnosis completed', time: '2026-03-16T10:31:00Z', type: 'ai' },
    { id: 't4', event: 'Contractor quotes requested (3)', time: '2026-03-16T10:32:00Z', type: 'action' },
    { id: 't5', event: 'All quotes received', time: '2026-03-16T14:15:00Z', type: 'update' },
  ],
};

const urgencyBadge: Record<string, { label: string; variant: 'danger' | 'warning' | 'success' }> = {
  emergency: { label: 'Emergency', variant: 'danger' }, urgent: { label: 'Urgent', variant: 'warning' }, routine: { label: 'Routine', variant: 'success' },
};
const statusBadge: Record<string, { label: string; variant: 'info' | 'neutral' | 'success' }> = {
  open: { label: 'Open', variant: 'neutral' }, in_progress: { label: 'In Progress', variant: 'info' }, completed: { label: 'Completed', variant: 'success' },
};

export default function MaintenanceDetail() {
  const navigate = useNavigate();
  const [showDiagnosis, setShowDiagnosis] = useState(true);

  const { data: request } = useQuery({
    queryKey: ['maintenance', '1'],
    queryFn: async () => { const res = await api.get('/maintenance/1'); return res.data; },
    placeholderData: mockRequest,
  });

  const r = request ?? mockRequest;
  const urg = urgencyBadge[r.urgency]; const stat = statusBadge[r.status];

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => navigate('/maintenance')} className="flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-700 mb-3 transition-colors"><ArrowLeft className="w-4 h-4" />Back to Maintenance</button>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1"><span className="text-xs font-mono font-semibold text-zinc-400">{r.ticketNumber}</span><Badge variant={urg.variant} dot>{urg.label}</Badge><Badge variant={stat.variant} dot>{stat.label}</Badge></div>
            <h1 className="text-2xl font-bold text-zinc-900">{r.title}</h1>
            <p className="text-sm text-zinc-500 mt-1">{r.unit} - {r.property} &middot; Reported by {r.tenant}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowDiagnosis(!showDiagnosis)} className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-700 transition-colors"><Bot className="w-4 h-4" />Run AI Diagnosis</button>
            <button className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 transition-colors"><CheckCircle2 className="w-4 h-4" />Mark Complete</button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
            <h2 className="text-base font-semibold text-zinc-900 mb-2">Description</h2>
            <p className="text-sm text-zinc-700 leading-relaxed">{r.description}</p>
            <div className="flex items-center gap-2 mt-3"><Badge variant="neutral">{r.category}</Badge><span className="text-xs text-zinc-400"><Clock className="w-3 h-3 inline mr-1" />{formatDistanceToNow(new Date(r.createdAt), { addSuffix: true })}</span></div>
          </div>

          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-zinc-900">Photos</h2><button className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"><Camera className="w-4 h-4" /> Add Photo</button></div>
            <div className="grid grid-cols-3 gap-3">{r.photos.map((p: number) => (<div key={p} className="aspect-square rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-300"><Camera className="w-8 h-8" /></div>))}</div>
          </div>

          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
            <h2 className="text-base font-semibold text-zinc-900 mb-3">Contractor Quotes</h2>
            <div className="space-y-3">
              {r.quotes.map((q: typeof mockRequest.quotes[0]) => (
                <div key={q.id} className="flex items-center justify-between p-4 rounded-lg border border-zinc-200 hover:border-zinc-300 transition-colors">
                  <div><div className="font-semibold text-sm text-zinc-900">{q.contractor}</div><div className="text-xs text-zinc-500 mt-0.5">ETA: {q.eta}</div></div>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-zinc-900">${q.amount}</span>
                    <button className="p-2 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors"><ThumbsUp className="w-4 h-4" /></button>
                    <button className="p-2 rounded-lg bg-red-50 text-red-500 hover:bg-red-100 transition-colors"><ThumbsDown className="w-4 h-4" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {showDiagnosis && r.aiDiagnosis && (
            <div className="bg-white rounded-xl border border-purple-200 shadow-sm p-5 ring-1 ring-purple-100">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center"><Bot className="w-4 h-4 text-purple-600" /></div>
                <div><h2 className="text-base font-semibold text-zinc-900">AI Diagnosis</h2><p className="text-xs text-zinc-500">{r.aiDiagnosis.confidence}% confidence</p></div>
              </div>
              <div className="space-y-4">
                <div><span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Category</span><p className="text-sm font-semibold text-zinc-900 mt-0.5">{r.aiDiagnosis.category}</p></div>
                <div>
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Severity</span>
                  <div className="mt-1.5 w-full bg-zinc-100 rounded-full h-2.5"><div className={clsx('h-2.5 rounded-full transition-all', r.aiDiagnosis.severity >= 70 ? 'bg-red-500' : r.aiDiagnosis.severity >= 40 ? 'bg-amber-500' : 'bg-emerald-500')} style={{ width: `${r.aiDiagnosis.severity}%` }} /></div>
                  <p className="text-xs text-zinc-500 mt-1">{r.aiDiagnosis.severity}/100</p>
                </div>
                <div><span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Recommended Action</span><p className="text-sm text-zinc-700 mt-0.5 leading-relaxed">{r.aiDiagnosis.recommendedAction}</p></div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50"><DollarSign className="w-4 h-4 text-blue-600" /><span className="text-sm font-semibold text-blue-900">Est. Cost: ${r.aiDiagnosis.estimatedCost.low} - ${r.aiDiagnosis.estimatedCost.high}</span></div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
            <h2 className="text-base font-semibold text-zinc-900 mb-4">Timeline</h2>
            <div className="space-y-4">
              {r.timeline.map((event: typeof mockRequest.timeline[0], idx: number) => (
                <div key={event.id} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className={clsx('w-6 h-6 rounded-full flex items-center justify-center shrink-0', event.type === 'ai' ? 'bg-purple-100' : event.type === 'created' ? 'bg-blue-100' : 'bg-zinc-100')}>
                      {event.type === 'ai' ? <Zap className="w-3 h-3 text-purple-600" /> : event.type === 'created' ? <AlertTriangle className="w-3 h-3 text-blue-600" /> : <Wrench className="w-3 h-3 text-zinc-500" />}
                    </div>
                    {idx < r.timeline.length - 1 && <div className="w-px h-full bg-zinc-200 mt-1" />}
                  </div>
                  <div className="pb-4"><p className="text-sm text-zinc-800">{event.event}</p><p className="text-xs text-zinc-400 mt-0.5">{formatDistanceToNow(new Date(event.time), { addSuffix: true })}</p></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
