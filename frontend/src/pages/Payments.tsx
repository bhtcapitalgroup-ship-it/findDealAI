import { useState, useEffect } from 'react';
import {
  CheckCircle2, Clock, AlertTriangle, ChevronLeft, ChevronRight, Plus, Star, X,
} from 'lucide-react';
import { formatCurrency, formatPercent } from '@/lib/utils';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import { paymentsApi } from '@/lib/api';

type PaymentStatus = 'paid' | 'pending' | 'overdue';
type PaymentMethod = 'ACH' | 'Stripe' | 'Zelle' | 'Check' | 'Cash' | '';
type FilterTab = 'all' | 'paid' | 'pending' | 'overdue';

interface PaymentRow {
  id: number;
  tenant: string;
  unit: string;
  property: string;
  amountDue: number;
  amountPaid: number;
  status: PaymentStatus;
  method: PaymentMethod;
  datePaid: string;
}

const mockPayments: PaymentRow[] = [
  { id: 1, tenant: 'James Smith', unit: '1A', property: 'Maple Street', amountDue: 1350, amountPaid: 1350, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 2, tenant: 'Maria Garcia', unit: '1B', property: 'Maple Street', amountDue: 1350, amountPaid: 1350, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 3, tenant: 'David Johnson', unit: '2A', property: 'Maple Street', amountDue: 1650, amountPaid: 1650, status: 'paid', method: 'Stripe', datePaid: 'Mar 2' },
  { id: 4, tenant: 'Sarah Williams', unit: '2B', property: 'Maple Street', amountDue: 1650, amountPaid: 0, status: 'pending', method: '', datePaid: '' },
  { id: 5, tenant: 'Michael Brown', unit: '3A', property: 'Maple Street', amountDue: 1800, amountPaid: 1800, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 6, tenant: 'Jennifer Davis', unit: '3B', property: 'Maple Street', amountDue: 1800, amountPaid: 1800, status: 'paid', method: 'Zelle', datePaid: 'Mar 3' },
  { id: 7, tenant: 'Robert Miller', unit: '4A', property: 'Maple Street', amountDue: 2100, amountPaid: 2100, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 8, tenant: 'Lisa Wilson', unit: '4B', property: 'Maple Street', amountDue: 2100, amountPaid: 0, status: 'pending', method: '', datePaid: '' },
  { id: 9, tenant: 'Kevin Moore', unit: '5A', property: 'Maple Street', amountDue: 1300, amountPaid: 1300, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 10, tenant: 'Amanda Taylor', unit: '5B', property: 'Maple Street', amountDue: 1300, amountPaid: 1300, status: 'paid', method: 'Check', datePaid: 'Mar 5' },
  { id: 11, tenant: 'Chris Anderson', unit: '6A', property: 'Maple Street', amountDue: 1600, amountPaid: 1600, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 12, tenant: 'Emily Thomas', unit: '101', property: 'Oak Park', amountDue: 1900, amountPaid: 1900, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 13, tenant: 'Daniel Jackson', unit: '102', property: 'Oak Park', amountDue: 1900, amountPaid: 1900, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 14, tenant: 'Rachel White', unit: '103', property: 'Oak Park', amountDue: 2200, amountPaid: 2200, status: 'paid', method: 'Stripe', datePaid: 'Mar 2' },
  { id: 15, tenant: 'Josh Harris', unit: '104', property: 'Oak Park', amountDue: 2200, amountPaid: 2200, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 16, tenant: 'Stephanie Martin', unit: '105', property: 'Oak Park', amountDue: 1900, amountPaid: 1900, status: 'paid', method: 'Zelle', datePaid: 'Mar 4' },
  { id: 17, tenant: 'Brian Thompson', unit: '106', property: 'Oak Park', amountDue: 1900, amountPaid: 1900, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 18, tenant: 'Nicole Robinson', unit: '107', property: 'Oak Park', amountDue: 2200, amountPaid: 2200, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 19, tenant: 'Tyler Clark', unit: 'A', property: 'Cedar Heights', amountDue: 2000, amountPaid: 2000, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 20, tenant: 'Megan Lewis', unit: 'B', property: 'Cedar Heights', amountDue: 2000, amountPaid: 2000, status: 'paid', method: 'Stripe', datePaid: 'Mar 2' },
  { id: 21, tenant: 'Andrew Lee', unit: 'C', property: 'Cedar Heights', amountDue: 2400, amountPaid: 2400, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
  { id: 22, tenant: 'Ashley Walker', unit: 'D', property: 'Cedar Heights', amountDue: 2400, amountPaid: 2400, status: 'paid', method: 'ACH', datePaid: 'Mar 1' },
];

const mockTotalDue = 38400;
const mockTotalCollected = 35450;
const mockTotalPending = 1650;
const mockTotalOverdue = 1300;
const mockCollectionPct = 92.3;

const mockPropertyStats = [
  { name: 'Maple Street', paid: 10, total: 11, collected: 18050, due: 19700 },
  { name: 'Oak Park', paid: 6, total: 7, collected: 11400, due: 14300 },
  { name: 'Cedar Heights', paid: 4, total: 4, collected: 8800, due: 8800 },
];

const statusBadge: Record<PaymentStatus, { label: string; variant: 'success' | 'warning' | 'danger' }> = {
  paid: { label: 'Paid', variant: 'success' },
  pending: { label: 'Pending', variant: 'warning' },
  overdue: { label: 'Overdue', variant: 'danger' },
};

const filterTabs: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'paid', label: 'Paid' },
  { key: 'pending', label: 'Pending' },
  { key: 'overdue', label: 'Overdue' },
];

export default function Payments() {
  const [filter, setFilter] = useState<FilterTab>('all');
  const [showModal, setShowModal] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('ACH');
  const [paymentDate, setPaymentDate] = useState('2026-03-16');
  const [paymentNotes, setPaymentNotes] = useState('');

  const [payments, setPayments] = useState<PaymentRow[]>(mockPayments);
  const [totalDue, setTotalDue] = useState(mockTotalDue);
  const [totalCollected, setTotalCollected] = useState(mockTotalCollected);
  const [totalPending, setTotalPending] = useState(mockTotalPending);
  const [totalOverdue, setTotalOverdue] = useState(mockTotalOverdue);
  const [collectionPct, setCollectionPct] = useState(mockCollectionPct);
  const [propertyStats, setPropertyStats] = useState(mockPropertyStats);

  useEffect(() => {
    // Try fetching payments list
    paymentsApi.list().then((data) => {
      if (Array.isArray(data) && data.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setPayments((data as any[]).map((p: any, i: number): PaymentRow => ({
          id: Number(p.id || i + 1),
          tenant: String(p.tenant_name || p.tenant || ''),
          unit: String(p.unit || p.unit_number || ''),
          property: String(p.property || p.property_name || ''),
          amountDue: Number(p.amount_due || p.amountDue || p.amount || 0),
          amountPaid: Number(p.amount_paid || p.amountPaid || 0),
          status: (String(p.status || 'pending') as PaymentStatus),
          method: (String(p.method || p.payment_method || '') as PaymentMethod),
          datePaid: String(p.date_paid || p.datePaid || p.paid_date || ''),
        })));
      }
    }).catch(() => {});

    // Try fetching payment summary
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    paymentsApi.summary().then((data: any) => {
      if (data) {
        if (data.total_due != null) setTotalDue(Number(data.total_due));
        if (data.total_collected != null) setTotalCollected(Number(data.total_collected));
        if (data.total_pending != null) setTotalPending(Number(data.total_pending));
        if (data.total_overdue != null) setTotalOverdue(Number(data.total_overdue));
        if (data.collection_rate != null) setCollectionPct(Number(data.collection_rate));
        if (Array.isArray(data.by_property)) {
          setPropertyStats((data.by_property as any[]).map((ps: any) => ({
            name: String(ps.name || ''),
            paid: Number(ps.paid || 0),
            total: Number(ps.total || 0),
            collected: Number(ps.collected || 0),
            due: Number(ps.due || 0),
          })));
        }
      }
    }).catch(() => {});
  }, []);

  const filtered = filter === 'all' ? payments : payments.filter((p) => p.status === filter);

  const unpaidTenants = payments.filter((p) => p.status !== 'paid');

  const selectedTenantData = unpaidTenants.find(
    (p) => `${p.tenant} - Unit ${p.unit}, ${p.property}` === selectedTenant
  );

  const computedStatus = (): string => {
    if (!paymentAmount || Number(paymentAmount) === 0) return 'Pending';
    if (selectedTenantData && Number(paymentAmount) >= selectedTenantData.amountDue) return 'Paid';
    return 'Partial';
  };

  const handleOpenModal = () => {
    if (unpaidTenants.length > 0) {
      const first = unpaidTenants[0];
      setSelectedTenant(`${first.tenant} - Unit ${first.unit}, ${first.property}`);
      setPaymentAmount('');
    }
    setPaymentMethod('ACH');
    setPaymentDate('2026-03-16');
    setPaymentNotes('');
    setShowModal(true);
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-7xl mx-auto space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900">Rent Collection</h1>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-white border border-zinc-200 rounded-lg px-3 py-1.5 shadow-sm">
              <button className="p-0.5 text-zinc-400 hover:text-zinc-600 transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm font-semibold text-zinc-800 min-w-[120px] text-center">March 2026</span>
              <button className="p-0.5 text-zinc-400 hover:text-zinc-600 transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <button
              onClick={handleOpenModal}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white text-sm font-semibold rounded-lg hover:bg-zinc-800 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Record Payment
            </button>
          </div>
        </div>

        {/* Collection Progress */}
        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-zinc-900">Collection Progress</h2>
            <span className="text-2xl font-bold text-zinc-900">{formatPercent(collectionPct)}</span>
          </div>
          <div className="w-full h-4 bg-zinc-100 rounded-full overflow-hidden mb-4">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all"
              style={{ width: `${collectionPct}%` }}
            />
          </div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-zinc-500">
              <span className="font-semibold text-zinc-800">{formatCurrency(totalCollected)}</span> of {formatCurrency(totalDue)} collected
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full text-sm font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Collected {formatCurrency(totalCollected)}
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full text-sm font-medium">
              <Clock className="w-3.5 h-3.5" />
              Pending {formatCurrency(totalPending)}
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 text-red-700 rounded-full text-sm font-medium">
              <AlertTriangle className="w-3.5 h-3.5" />
              Overdue {formatCurrency(totalOverdue)}
            </div>
          </div>
        </div>

        {/* Payment Status by Property */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {propertyStats.map((prop) => {
            const pct = (prop.collected / prop.due) * 100;
            const isFull = pct === 100;
            return (
              <div key={prop.name} className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-zinc-900">{prop.name}</h3>
                  {isFull && <Star className="w-4 h-4 text-amber-400 fill-amber-400" />}
                </div>
                <div className="w-full h-2 bg-zinc-100 rounded-full overflow-hidden mb-2">
                  <div
                    className={`h-full rounded-full transition-all ${isFull ? 'bg-amber-400' : 'bg-emerald-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-500">
                    <span className="font-semibold text-zinc-800">{prop.paid}/{prop.total}</span> units paid
                  </span>
                  <span className="text-zinc-500">
                    <span className="font-semibold text-zinc-800">{formatCurrency(prop.collected)}</span>/{formatCurrency(prop.due)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Payments Table */}
        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm">
          {/* Filter Tabs */}
          <div className="border-b border-zinc-200 px-5 pt-4">
            <div className="flex items-center gap-1">
              {filterTabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    filter === tab.key
                      ? 'bg-zinc-100 text-zinc-900 border-b-2 border-zinc-900'
                      : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
                  }`}
                >
                  {tab.label}
                  {tab.key !== 'all' && (
                    <span className="ml-1.5 text-xs px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-500">
                      {payments.filter((p) => p.status === tab.key).length}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50/50">
                  {['Tenant', 'Unit', 'Property', 'Amount Due', 'Amount Paid', 'Status', 'Method', 'Date Paid'].map((h) => (
                    <th
                      key={h}
                      className={`py-3 px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider sticky top-0 bg-zinc-50/50 ${
                        ['Amount Due', 'Amount Paid'].includes(h) ? 'text-right' : 'text-left'
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => {
                  const badge = statusBadge[row.status];
                  return (
                    <tr key={row.id} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50 transition-colors">
                      <td className="py-3 px-4 font-medium text-zinc-900">{row.tenant}</td>
                      <td className="py-3 px-4 text-zinc-600">{row.unit}</td>
                      <td className="py-3 px-4 text-zinc-600">{row.property}</td>
                      <td className="py-3 px-4 text-right text-zinc-700 font-medium">{formatCurrency(row.amountDue)}</td>
                      <td className="py-3 px-4 text-right font-medium">
                        {row.amountPaid > 0 ? (
                          <span className="text-emerald-600">{formatCurrency(row.amountPaid)}</span>
                        ) : (
                          <span className="text-zinc-300">&mdash;</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={badge.variant} dot>{badge.label}</Badge>
                      </td>
                      <td className="py-3 px-4 text-zinc-600">{row.method || <span className="text-zinc-300">&mdash;</span>}</td>
                      <td className="py-3 px-4 text-zinc-600">{row.datePaid || <span className="text-zinc-300">&mdash;</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Record Payment Modal */}
        <Modal open={showModal} onClose={() => setShowModal(false)} title="Record Payment" size="md">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              setShowModal(false);
            }}
          >
            {/* Tenant */}
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Tenant</label>
              <select
                value={selectedTenant}
                onChange={(e) => {
                  setSelectedTenant(e.target.value);
                  setPaymentAmount('');
                }}
                className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {unpaidTenants.map((p) => (
                  <option key={p.id} value={`${p.tenant} - Unit ${p.unit}, ${p.property}`}>
                    {p.tenant} - Unit {p.unit}, {p.property}
                  </option>
                ))}
              </select>
            </div>

            {/* Amount Due (read-only) */}
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Amount Due</label>
              <input
                type="text"
                readOnly
                value={selectedTenantData ? formatCurrency(selectedTenantData.amountDue) : ''}
                className="w-full px-3 py-2.5 text-sm border border-zinc-200 rounded-lg bg-zinc-50 text-zinc-500 cursor-not-allowed"
              />
            </div>

            {/* Amount Paid */}
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Amount Paid</label>
              <input
                type="number"
                min={0}
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder={selectedTenantData ? String(selectedTenantData.amountDue) : '0'}
                className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Method + Date */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-1">Payment Method</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option>ACH</option>
                  <option>Stripe</option>
                  <option>Zelle</option>
                  <option>Cash</option>
                  <option>Check</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-1">Payment Date</label>
                <input
                  type="date"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Notes <span className="text-zinc-400">(optional)</span></label>
              <textarea
                value={paymentNotes}
                onChange={(e) => setPaymentNotes(e.target.value)}
                rows={2}
                placeholder="Add any notes..."
                className="w-full px-3 py-2.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Auto-calculated status */}
            <div className="flex items-center gap-2 px-3 py-2 bg-zinc-50 rounded-lg border border-zinc-200">
              <span className="text-xs font-medium text-zinc-500">Status:</span>
              <span className={`text-xs font-semibold ${
                computedStatus() === 'Paid' ? 'text-emerald-600' :
                computedStatus() === 'Partial' ? 'text-amber-600' : 'text-zinc-400'
              }`}>
                {computedStatus()}
              </span>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-semibold text-white bg-zinc-900 rounded-lg hover:bg-zinc-800 transition-colors"
              >
                Record Payment
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </div>
  );
}
