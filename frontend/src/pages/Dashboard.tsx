import { useNavigate } from 'react-router-dom';
import {
  Building2, Users, DollarSign, AlertCircle, TrendingUp, Wrench,
  BarChart3, Percent, Bot, Plus, ArrowRight,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import StatCard from '../components/StatCard';

const rentData = [
  { month: 'Oct', collected: 42500, expected: 45000 },
  { month: 'Nov', collected: 44200, expected: 45000 },
  { month: 'Dec', collected: 43800, expected: 45000 },
  { month: 'Jan', collected: 44900, expected: 46500 },
  { month: 'Feb', collected: 45800, expected: 46500 },
  { month: 'Mar', collected: 46200, expected: 46500 },
];

const aiActivity = [
  { id: 1, action: 'Responded to tenant inquiry about lease renewal', tenant: 'Sarah Johnson', time: '5 min ago' },
  { id: 2, action: 'Diagnosed maintenance request: HVAC compressor failure', tenant: 'Unit 4B - Oak Manor', time: '22 min ago' },
  { id: 3, action: 'Sent rent reminder to 3 tenants', tenant: 'Multiple units', time: '1 hr ago' },
  { id: 4, action: 'Escalated noise complaint for landlord review', tenant: 'Mike Chen - Unit 2A', time: '2 hrs ago' },
  { id: 5, action: 'Approved contractor quote for plumbing repair ($280)', tenant: 'Unit 7 - Elm Street', time: '3 hrs ago' },
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">Overview of your property portfolio</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Units" value="24" icon={Building2} trend={{ value: '2', positive: true }} />
        <StatCard label="Occupancy Rate" value="91.7%" icon={Users} trend={{ value: '4.2%', positive: true }} />
        <StatCard label="Rent Collected" value="$46,200" icon={DollarSign} trend={{ value: '3.1%', positive: true }} />
        <StatCard label="Outstanding" value="$2,400" icon={AlertCircle} trend={{ value: '12%', positive: false }} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Net Operating Income" value="$31,850" icon={TrendingUp} />
        <StatCard label="Cash Flow" value="$18,200" icon={BarChart3} />
        <StatCard label="Cap Rate" value="7.2%" icon={Percent} />
        <StatCard label="Maintenance Spend" value="$3,450" icon={Wrench} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-zinc-900">Rent Collection</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Last 6 months trend</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-600" />Collected</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-zinc-300" />Expected</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={rentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} formatter={(value: any) => [`$${value.toLocaleString()}`, '']} />
              <Line type="monotone" dataKey="expected" stroke="#cbd5e1" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              <Line type="monotone" dataKey="collected" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 4, fill: '#2563eb', strokeWidth: 0 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
          <h2 className="text-base font-semibold text-zinc-900 mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button onClick={() => navigate('/properties')} className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors text-sm font-medium"><Plus className="w-4 h-4" />Add Property</button>
            <button onClick={() => navigate('/tenants')} className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors text-sm font-medium"><Users className="w-4 h-4" />Add Tenant</button>
            <button onClick={() => navigate('/maintenance')} className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors text-sm font-medium"><Wrench className="w-4 h-4" />View Maintenance</button>
            <button onClick={() => navigate('/messages')} className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors text-sm font-medium"><Bot className="w-4 h-4" />AI Conversations</button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center"><Bot className="w-4 h-4 text-purple-600" /></div>
            <div>
              <h2 className="text-base font-semibold text-zinc-900">AI Activity</h2>
              <p className="text-xs text-zinc-500">Recent automated actions</p>
            </div>
          </div>
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">View all <ArrowRight className="w-3.5 h-3.5" /></button>
        </div>
        <div className="space-y-3">
          {aiActivity.map((item) => (
            <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-zinc-50 transition-colors">
              <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center shrink-0 mt-0.5"><Bot className="w-4 h-4 text-zinc-500" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-800">{item.action}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{item.tenant}</p>
              </div>
              <span className="text-xs text-zinc-400 whitespace-nowrap shrink-0">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
