import { useState } from 'react';
import { Save, CreditCard, Bot, Bell, User } from 'lucide-react';
import { useAuth } from '../lib/auth';

export default function Settings() {
  const { user } = useAuth();
  const [autoApprove, setAutoApprove] = useState(500);
  const [escalationSensitivity, setEscalationSensitivity] = useState('medium');
  const [notifications, setNotifications] = useState({
    emailMaintenance: true, emailPayments: true, emailEscalations: true,
    smsMaintenance: false, smsPayments: true, smsEscalations: true,
  });

  const toggleNotif = (key: keyof typeof notifications) => setNotifications((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="max-w-3xl space-y-8">
      <div><h1 className="text-2xl font-bold text-zinc-900">Settings</h1><p className="text-sm text-zinc-500 mt-1">Manage your account and preferences</p></div>

      <section className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5"><div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center"><User className="w-[18px] h-[18px] text-blue-600" /></div><h2 className="text-base font-semibold text-zinc-900">Account Information</h2></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Full Name</label><input type="text" defaultValue={user ? `${user.first_name} ${user.last_name}` : ''} className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Email</label><input type="email" defaultValue={user?.email || ''} className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Phone</label><input type="tel" defaultValue="(503) 555-0100" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
          <div><label className="block text-sm font-medium text-zinc-700 mb-1">Company</label><input type="text" defaultValue="Mitchell Property Management" className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" /></div>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5"><div className="w-9 h-9 rounded-lg bg-purple-50 flex items-center justify-center"><Bot className="w-[18px] h-[18px] text-purple-600" /></div><h2 className="text-base font-semibold text-zinc-900">AI Preferences</h2></div>
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Auto-Approve Threshold</label>
            <p className="text-xs text-zinc-500 mb-2">AI can automatically approve maintenance quotes below this amount</p>
            <div className="flex items-center gap-3"><input type="range" min={0} max={2000} step={50} value={autoApprove} onChange={(e) => setAutoApprove(Number(e.target.value))} className="flex-1 accent-purple-600" /><span className="text-sm font-semibold text-zinc-900 w-16 text-right">${autoApprove}</span></div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Escalation Sensitivity</label>
            <p className="text-xs text-zinc-500 mb-2">How quickly AI should escalate conversations to you</p>
            <div className="flex gap-2">{['low', 'medium', 'high'].map((level) => (<button key={level} onClick={() => setEscalationSensitivity(level)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${escalationSensitivity === level ? 'bg-purple-600 text-white' : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'}`}>{level.charAt(0).toUpperCase() + level.slice(1)}</button>))}</div>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5"><div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center"><CreditCard className="w-[18px] h-[18px] text-emerald-600" /></div><h2 className="text-base font-semibold text-zinc-900">Payment Setup</h2></div>
        <div className="flex items-center justify-between p-4 rounded-lg border border-zinc-200 bg-zinc-50">
          <div><p className="text-sm font-semibold text-zinc-900">Stripe Connect</p><p className="text-xs text-zinc-500 mt-0.5">Accept online rent payments from tenants</p></div>
          <div className="flex items-center gap-3"><span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600"><span className="w-2 h-2 rounded-full bg-emerald-500" />Connected</span><button className="text-sm text-blue-600 hover:text-blue-700 font-medium">Manage</button></div>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5"><div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center"><Bell className="w-[18px] h-[18px] text-amber-600" /></div><h2 className="text-base font-semibold text-zinc-900">Notification Preferences</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-zinc-200"><th className="text-left py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Category</th><th className="text-center py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider w-24">Email</th><th className="text-center py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider w-24">SMS</th></tr></thead>
            <tbody>
              {[{ label: 'Maintenance Updates', emailKey: 'emailMaintenance' as const, smsKey: 'smsMaintenance' as const }, { label: 'Payment Notifications', emailKey: 'emailPayments' as const, smsKey: 'smsPayments' as const }, { label: 'AI Escalations', emailKey: 'emailEscalations' as const, smsKey: 'smsEscalations' as const }].map((row) => (
                <tr key={row.label} className="border-b border-zinc-100">
                  <td className="py-3 text-zinc-700 font-medium">{row.label}</td>
                  <td className="py-3 text-center"><button onClick={() => toggleNotif(row.emailKey)} className={`w-10 h-6 rounded-full transition-colors relative ${notifications[row.emailKey] ? 'bg-blue-600' : 'bg-zinc-300'}`}><span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${notifications[row.emailKey] ? 'left-5' : 'left-1'}`} /></button></td>
                  <td className="py-3 text-center"><button onClick={() => toggleNotif(row.smsKey)} className={`w-10 h-6 rounded-full transition-colors relative ${notifications[row.smsKey] ? 'bg-blue-600' : 'bg-zinc-300'}`}><span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${notifications[row.smsKey] ? 'left-5' : 'left-1'}`} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex justify-end pb-8"><button className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"><Save className="w-4 h-4" />Save Changes</button></div>
    </div>
  );
}
