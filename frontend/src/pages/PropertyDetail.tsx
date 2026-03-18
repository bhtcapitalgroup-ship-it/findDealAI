import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Building2, DollarSign, TrendingUp, Percent,
  Home, Users, Wrench, CreditCard, Calendar, Edit3, ChevronRight,
} from 'lucide-react';
import clsx from 'clsx';
import { formatCurrency, formatPercent } from '@/lib/utils';
import Badge from '../components/Badge';
import DataTable, { type Column } from '../components/DataTable';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface UnitData {
  id: string;
  unitNumber: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  monthlyRent: number;
  status: 'occupied' | 'vacant';
  tenant: string | null;
  leaseEnd: string | null;
}

interface RecentExpense {
  id: string;
  date: string;
  description: string;
  category: string;
  amount: number;
}

interface PropertyFull {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  type: string;
  status: string;
  purchasePrice: number;
  currentValue: number;
  loanAmount: number;
  monthlyMortgage: number;
  annualTax: number;
  annualInsurance: number;
  monthlyHOA: number;
  monthlyManagement: number;
  monthlyMaintenance: number;
  lender: string;
  interestRate: number;
  loanTerm: number;
  monthlyEscrow: number;
  purchaseDate: string;
  yearBuilt: number;
  closingCosts: number;
  rehabCosts: number;
  downPayment: number;
  units: UnitData[];
  recentExpenses: RecentExpense[];
}

// ---------------------------------------------------------------------------
// Mock Data
// ---------------------------------------------------------------------------
const mockProperties: Record<string, PropertyFull> = {
  '1': {
    id: '1',
    name: 'Maple Street Apartments',
    address: '742 Maple St',
    city: 'Portland',
    state: 'OR',
    zip: '97201',
    type: 'Multi-Family',
    status: 'Active',
    purchasePrice: 2_400_000,
    currentValue: 2_800_000,
    loanAmount: 1_920_000,
    monthlyMortgage: 9_800,
    annualTax: 28_000,
    annualInsurance: 10_200,
    monthlyHOA: 0,
    monthlyManagement: 1_970,
    monthlyMaintenance: 800,
    lender: 'Pacific Northwest Bank',
    interestRate: 6.25,
    loanTerm: 30,
    monthlyEscrow: 450,
    purchaseDate: '2021-06-15',
    yearBuilt: 1998,
    closingCosts: 36_000,
    rehabCosts: 85_000,
    downPayment: 480_000,
    units: [
      { id: 'u1', unitNumber: '1A', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied', tenant: 'Sarah Johnson', leaseEnd: '2026-08-31' },
      { id: 'u2', unitNumber: '1B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied', tenant: 'Mike Chen', leaseEnd: '2026-11-30' },
      { id: 'u3', unitNumber: '2A', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_750, status: 'occupied', tenant: 'Lisa Park', leaseEnd: '2026-07-31' },
      { id: 'u4', unitNumber: '2B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_750, status: 'vacant', tenant: null, leaseEnd: null },
      { id: 'u5', unitNumber: '3A', bedrooms: 3, bathrooms: 2, sqft: 1_100, monthlyRent: 2_100, status: 'occupied', tenant: 'James Smith', leaseEnd: '2027-01-31' },
      { id: 'u6', unitNumber: '3B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied', tenant: 'Emma Wilson', leaseEnd: '2026-09-30' },
      { id: 'u7', unitNumber: '4A', bedrooms: 2, bathrooms: 2, sqft: 950, monthlyRent: 1_800, status: 'occupied', tenant: 'David Kim', leaseEnd: '2026-06-30' },
      { id: 'u8', unitNumber: '4B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied', tenant: 'Amy Taylor', leaseEnd: '2026-12-31' },
      { id: 'u9', unitNumber: '5A', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied', tenant: 'Robert Garcia', leaseEnd: '2027-03-31' },
      { id: 'u10', unitNumber: '5B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied', tenant: 'Nina Patel', leaseEnd: '2026-10-31' },
      { id: 'u11', unitNumber: '6A', bedrooms: 3, bathrooms: 2, sqft: 1_100, monthlyRent: 2_100, status: 'occupied', tenant: 'Carlos Rivera', leaseEnd: '2027-02-28' },
      { id: 'u12', unitNumber: '6B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied', tenant: 'Jennifer Lee', leaseEnd: '2026-05-31' },
    ],
    recentExpenses: [
      { id: 'e1', date: '2026-03-10', description: 'HVAC repair — Unit 3A', category: 'Repair', amount: 1_250 },
      { id: 'e2', date: '2026-02-25', description: 'Plumbing leak — Unit 1B', category: 'Repair', amount: 480 },
      { id: 'e3', date: '2026-02-14', description: 'Common area landscaping', category: 'Maintenance', amount: 650 },
      { id: 'e4', date: '2026-01-28', description: 'Roof inspection', category: 'Inspection', amount: 350 },
      { id: 'e5', date: '2026-01-12', description: 'Hallway lighting upgrade', category: 'Improvement', amount: 890 },
    ],
  },
  '2': {
    id: '2',
    name: 'Oak Park Townhomes',
    address: '1200 Oak Park Dr',
    city: 'Portland',
    state: 'OR',
    zip: '97205',
    type: 'Townhouse',
    status: 'Active',
    purchasePrice: 1_600_000,
    currentValue: 1_900_000,
    loanAmount: 1_280_000,
    monthlyMortgage: 6_500,
    annualTax: 19_000,
    annualInsurance: 7_200,
    monthlyHOA: 200,
    monthlyManagement: 1_430,
    monthlyMaintenance: 550,
    lender: 'Columbia Credit Union',
    interestRate: 5.875,
    loanTerm: 30,
    monthlyEscrow: 350,
    purchaseDate: '2022-03-10',
    yearBuilt: 2005,
    closingCosts: 24_000,
    rehabCosts: 40_000,
    downPayment: 320_000,
    units: [
      { id: 'u1', unitNumber: 'A', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied', tenant: 'Tom Bradley', leaseEnd: '2026-09-30' },
      { id: 'u2', unitNumber: 'B', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied', tenant: 'Rachel Green', leaseEnd: '2026-12-31' },
      { id: 'u3', unitNumber: 'C', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'occupied', tenant: 'Kevin Hart', leaseEnd: '2026-08-31' },
      { id: 'u4', unitNumber: 'D', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'vacant', tenant: null, leaseEnd: null },
      { id: 'u5', unitNumber: 'E', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied', tenant: 'Susan Park', leaseEnd: '2027-01-31' },
      { id: 'u6', unitNumber: 'F', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'occupied', tenant: 'Mark Davis', leaseEnd: '2026-07-31' },
      { id: 'u7', unitNumber: 'G', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 1_550, status: 'occupied', tenant: 'Laura Chen', leaseEnd: '2026-11-30' },
      { id: 'u8', unitNumber: 'H', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_500, status: 'occupied', tenant: 'James Wong', leaseEnd: '2027-04-30' },
    ],
    recentExpenses: [
      { id: 'e1', date: '2026-03-05', description: 'Gutter cleaning', category: 'Maintenance', amount: 320 },
      { id: 'e2', date: '2026-02-18', description: 'Unit D turnover painting', category: 'Turnover', amount: 1_100 },
      { id: 'e3', date: '2026-02-01', description: 'Parking lot repair', category: 'Repair', amount: 2_200 },
      { id: 'e4', date: '2026-01-15', description: 'Snow removal service', category: 'Maintenance', amount: 450 },
      { id: 'e5', date: '2026-01-05', description: 'Fire extinguisher inspection', category: 'Inspection', amount: 180 },
    ],
  },
  '3': {
    id: '3',
    name: 'Cedar Heights Condo',
    address: '890 Cedar Heights Way',
    city: 'Lake Oswego',
    state: 'OR',
    zip: '97034',
    type: 'Condo',
    status: 'Active',
    purchasePrice: 850_000,
    currentValue: 980_000,
    loanAmount: 680_000,
    monthlyMortgage: 3_400,
    annualTax: 10_500,
    annualInsurance: 4_200,
    monthlyHOA: 450,
    monthlyManagement: 880,
    monthlyMaintenance: 300,
    lender: 'Oregon First Mortgage',
    interestRate: 6.0,
    loanTerm: 30,
    monthlyEscrow: 250,
    purchaseDate: '2023-01-20',
    yearBuilt: 2012,
    closingCosts: 12_750,
    rehabCosts: 15_000,
    downPayment: 170_000,
    units: [
      { id: 'u1', unitNumber: '101', bedrooms: 2, bathrooms: 2, sqft: 1_050, monthlyRent: 2_200, status: 'occupied', tenant: 'Alex Morgan', leaseEnd: '2026-10-31' },
      { id: 'u2', unitNumber: '102', bedrooms: 2, bathrooms: 2, sqft: 1_050, monthlyRent: 2_200, status: 'occupied', tenant: 'Diana Prince', leaseEnd: '2026-06-30' },
      { id: 'u3', unitNumber: '201', bedrooms: 3, bathrooms: 2, sqft: 1_300, monthlyRent: 2_400, status: 'occupied', tenant: 'Bruce Wayne', leaseEnd: '2027-02-28' },
      { id: 'u4', unitNumber: '202', bedrooms: 1, bathrooms: 1, sqft: 750, monthlyRent: 2_000, status: 'occupied', tenant: 'Clark Kent', leaseEnd: '2026-08-31' },
    ],
    recentExpenses: [
      { id: 'e1', date: '2026-03-12', description: 'Elevator maintenance', category: 'Maintenance', amount: 750 },
      { id: 'e2', date: '2026-02-20', description: 'Lobby carpet cleaning', category: 'Maintenance', amount: 280 },
      { id: 'e3', date: '2026-02-08', description: 'Unit 102 garbage disposal', category: 'Repair', amount: 220 },
      { id: 'e4', date: '2026-01-22', description: 'Security camera upgrade', category: 'Improvement', amount: 1_400 },
      { id: 'e5', date: '2026-01-10', description: 'Pest control quarterly', category: 'Maintenance', amount: 350 },
    ],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function totalRent(p: PropertyFull) {
  return p.units.reduce((s, u) => s + u.monthlyRent, 0);
}
function occupiedUnits(p: PropertyFull) {
  return p.units.filter((u) => u.status === 'occupied');
}
function monthlyExpenses(p: PropertyFull) {
  return p.monthlyMortgage + p.annualTax / 12 + p.annualInsurance / 12 + p.monthlyHOA + p.monthlyManagement + p.monthlyMaintenance;
}
function monthlyCashFlow(p: PropertyFull) {
  return totalRent(p) - monthlyExpenses(p);
}
function annualNOI(p: PropertyFull) {
  const opex = p.annualTax + p.annualInsurance + p.monthlyHOA * 12 + p.monthlyManagement * 12 + p.monthlyMaintenance * 12;
  return totalRent(p) * 12 - opex;
}
function capRate(p: PropertyFull) {
  return (annualNOI(p) / p.currentValue) * 100;
}

const typeBadgeVariant: Record<string, 'info' | 'purple' | 'warning' | 'success' | 'neutral'> = {
  'Multi-Family': 'info',
  Townhouse: 'purple',
  Condo: 'warning',
  'Single Family': 'success',
  Commercial: 'neutral',
};

const expenseCategoryColor: Record<string, string> = {
  Repair: 'bg-red-50 text-red-700',
  Maintenance: 'bg-blue-50 text-blue-700',
  Inspection: 'bg-amber-50 text-amber-700',
  Improvement: 'bg-purple-50 text-purple-700',
  Turnover: 'bg-orange-50 text-orange-700',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const p = mockProperties[id || '1'] ?? mockProperties['1'];

  const rent = totalRent(p);
  const expenses = monthlyExpenses(p);
  const cf = monthlyCashFlow(p);
  const equity = p.currentValue - p.loanAmount;
  const noi = annualNOI(p);
  const cr = capRate(p);
  const occupied = occupiedUnits(p);

  // Estimate current balance (simplified — months elapsed * rough principal paydown)
  const purchaseMs = new Date(p.purchaseDate).getTime();
  const nowMs = Date.now();
  const monthsElapsed = Math.max(0, Math.round((nowMs - purchaseMs) / (1000 * 60 * 60 * 24 * 30.44)));
  const monthlyRate = p.interestRate / 100 / 12;
  const totalPayments = p.loanTerm * 12;
  const monthlyPaymentCalc = p.loanAmount * monthlyRate * Math.pow(1 + monthlyRate, totalPayments) / (Math.pow(1 + monthlyRate, totalPayments) - 1);
  // Remaining balance after n payments
  const remainingBalance = p.loanAmount * Math.pow(1 + monthlyRate, monthsElapsed) - (monthlyPaymentCalc * (Math.pow(1 + monthlyRate, monthsElapsed) - 1) / monthlyRate);
  const currentBalance = Math.max(0, Math.round(remainingBalance));
  const principalPaid = p.loanAmount - currentBalance;
  const monthlyInterest = Math.round(currentBalance * monthlyRate);
  const monthlyPrincipal = Math.round(monthlyPaymentCalc - monthlyInterest);
  const payoffProgress = ((p.loanAmount - currentBalance) / p.loanAmount) * 100;

  // Unit table columns
  const unitColumns: Column<UnitData>[] = [
    { key: 'unitNumber', label: 'Unit #', sortable: true, render: (row) => <span className="font-semibold text-zinc-900">{row.unitNumber}</span> },
    { key: 'bedrooms', label: 'Beds', sortable: true, render: (row) => String(row.bedrooms) },
    { key: 'bathrooms', label: 'Baths', sortable: true, render: (row) => String(row.bathrooms) },
    { key: 'sqft', label: 'Sqft', sortable: true, render: (row) => row.sqft.toLocaleString() },
    { key: 'monthlyRent', label: 'Rent', sortable: true, render: (row) => formatCurrency(row.monthlyRent) },
    {
      key: 'status', label: 'Status', sortable: true,
      render: (row) => (
        <Badge variant={row.status === 'occupied' ? 'success' : 'warning'} dot>
          {row.status === 'occupied' ? 'Occupied' : 'Vacant'}
        </Badge>
      ),
    },
    { key: 'tenant', label: 'Tenant', render: (row) => row.tenant || <span className="text-zinc-400 italic">--</span> },
    {
      key: 'leaseEnd', label: 'Lease End', sortable: true,
      render: (row) => row.leaseEnd ? new Date(row.leaseEnd).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : <span className="text-zinc-400">--</span>,
    },
  ];

  return (
    <div className="min-h-screen bg-zinc-50 space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/properties')}
          className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-700 mb-3 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Properties
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">{p.name}</h1>
            <div className="flex items-center gap-1.5 mt-1 text-sm text-zinc-500">
              <MapPin className="w-4 h-4" />
              {p.address}, {p.city}, {p.state} {p.zip}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant={typeBadgeVariant[p.type] || 'neutral'}>{p.type}</Badge>
              <Badge variant="success" dot>{p.status}</Badge>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-zinc-700 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 transition-colors shadow-sm">
            <Edit3 className="w-4 h-4" /> Edit Property
          </button>
        </div>
      </div>

      {/* Financial Overview — 6 metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'Purchase Price', value: formatCurrency(p.purchasePrice), icon: DollarSign, color: 'text-zinc-900' },
          { label: 'Current Value', value: formatCurrency(p.currentValue), icon: TrendingUp, color: 'text-zinc-900' },
          { label: 'Equity', value: formatCurrency(equity), icon: Building2, color: 'text-emerald-600' },
          { label: 'Monthly Cash Flow', value: formatCurrency(Math.round(cf)), icon: DollarSign, color: cf >= 0 ? 'text-emerald-600' : 'text-red-600' },
          { label: 'Annual NOI', value: formatCurrency(Math.round(noi)), icon: TrendingUp, color: noi >= 0 ? 'text-emerald-600' : 'text-red-600' },
          { label: 'Cap Rate', value: formatPercent(cr), icon: Percent, color: 'text-zinc-900' },
        ].map((item) => (
          <div key={item.label} className="bg-white rounded-xl border border-zinc-200 shadow-sm p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">{item.label}</span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                <item.icon className="w-4 h-4 text-blue-600" />
              </div>
            </div>
            <div className={clsx('text-2xl font-bold', item.color)}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Cost Breakdown Card */}
      <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-200">
          <h2 className="text-lg font-bold text-zinc-900">Cost Breakdown</h2>
        </div>
        <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-zinc-200">
          {/* Left: Monthly Income */}
          <div className="p-6">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mb-4">Monthly Income</h3>
            <div className="space-y-2">
              {p.units.map((u) => (
                <div key={u.id} className="flex items-center justify-between py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-700">Unit {u.unitNumber}</span>
                    {u.tenant && <span className="text-xs text-zinc-400">{u.tenant}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-900">{formatCurrency(u.monthlyRent)}</span>
                    <span className={clsx('w-2 h-2 rounded-full', u.status === 'occupied' ? 'bg-emerald-500' : 'bg-amber-400')} />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-3 border-t border-zinc-200 flex items-center justify-between">
              <span className="text-sm font-bold text-zinc-900">Total Monthly Income</span>
              <span className="text-lg font-bold text-emerald-600">{formatCurrency(rent)}</span>
            </div>
          </div>

          {/* Right: Monthly Expenses */}
          <div className="p-6">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mb-4">Monthly Expenses</h3>
            <div className="space-y-3">
              {[
                { label: 'Mortgage', value: p.monthlyMortgage },
                { label: 'Property Tax', value: Math.round(p.annualTax / 12) },
                { label: 'Insurance', value: Math.round(p.annualInsurance / 12) },
                { label: 'HOA', value: p.monthlyHOA, hide: p.monthlyHOA === 0 },
                { label: 'Property Management', value: p.monthlyManagement },
                { label: 'Maintenance (avg)', value: p.monthlyMaintenance },
              ]
                .filter((item) => !('hide' in item) || !item.hide)
                .map((item) => (
                  <div key={item.label} className="flex items-center justify-between py-1.5">
                    <span className="text-sm text-zinc-600">{item.label}</span>
                    <span className="text-sm font-semibold text-zinc-900">{formatCurrency(item.value)}</span>
                  </div>
                ))}
            </div>
            <div className="mt-4 pt-3 border-t border-zinc-200 flex items-center justify-between">
              <span className="text-sm font-bold text-zinc-900">Total Monthly Expenses</span>
              <span className="text-lg font-bold text-red-600">{formatCurrency(Math.round(expenses))}</span>
            </div>
          </div>
        </div>

        {/* Net Cash Flow Bar */}
        <div className="px-6 py-4 bg-zinc-50 border-t border-zinc-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-bold text-zinc-700">Net Monthly Cash Flow</span>
            <span className={clsx('text-xl font-bold', cf >= 0 ? 'text-emerald-600' : 'text-red-600')}>
              {cf >= 0 ? '+' : ''}{formatCurrency(Math.round(cf))}
            </span>
          </div>
          <div className="relative h-4 bg-zinc-200 rounded-full overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-emerald-500 rounded-full"
              style={{ width: `${Math.min(100, (rent / (rent + expenses)) * 100 * 2)}%` }}
            />
            <div
              className="absolute top-0 h-full bg-red-400 rounded-full"
              style={{
                left: `${Math.min(100, (rent / (rent + expenses)) * 100 * 2)}%`,
                width: `${Math.max(0, 100 - (rent / (rent + expenses)) * 100 * 2)}%`,
              }}
            />
            {/* Divider at expense threshold */}
            <div
              className="absolute top-0 h-full w-0.5 bg-zinc-900/30"
              style={{ left: `${(expenses / (rent > expenses ? rent : expenses)) * 100}%` }}
            />
          </div>
          <div className="flex justify-between mt-1.5 text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">
            <span>Income: {formatCurrency(rent)}</span>
            <span>Expenses: {formatCurrency(Math.round(expenses))}</span>
          </div>
        </div>
      </div>

      {/* Units Table */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-zinc-900">
            Units ({p.units.length})
            <span className="ml-2 text-sm font-normal text-zinc-500">
              {occupied.length} occupied, {p.units.length - occupied.length} vacant
            </span>
          </h2>
        </div>
        <DataTable columns={unitColumns} data={p.units} keyExtractor={(u) => u.id} />
      </div>

      {/* Mortgage Details & Recent Expenses side-by-side */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Mortgage Details */}
        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-200 flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-zinc-400" />
            <h2 className="text-lg font-bold text-zinc-900">Mortgage Details</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'Lender', value: p.lender },
                { label: 'Original Amount', value: formatCurrency(p.loanAmount) },
                { label: 'Current Balance', value: formatCurrency(currentBalance) },
                { label: 'Interest Rate', value: formatPercent(p.interestRate) },
                { label: 'Loan Term', value: `${p.loanTerm} years` },
                { label: 'Principal Paid', value: formatCurrency(principalPaid) },
              ].map((item) => (
                <div key={item.label}>
                  <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">{item.label}</div>
                  <div className="text-sm font-bold text-zinc-900 mt-0.5">{item.value}</div>
                </div>
              ))}
            </div>

            {/* Monthly payment breakdown */}
            <div className="border-t border-zinc-200 pt-4">
              <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mb-3">Monthly Payment Breakdown</div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-600">Principal</span>
                  <span className="font-semibold text-zinc-900">{formatCurrency(monthlyPrincipal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-600">Interest</span>
                  <span className="font-semibold text-zinc-900">{formatCurrency(monthlyInterest)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-600">Escrow</span>
                  <span className="font-semibold text-zinc-900">{formatCurrency(p.monthlyEscrow)}</span>
                </div>
                <div className="flex justify-between text-sm pt-2 border-t border-zinc-100">
                  <span className="font-bold text-zinc-900">Total Payment</span>
                  <span className="font-bold text-zinc-900">{formatCurrency(p.monthlyMortgage + p.monthlyEscrow)}</span>
                </div>
              </div>
            </div>

            {/* Payoff Timeline */}
            <div className="border-t border-zinc-200 pt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Payoff Progress</span>
                <span className="text-xs font-bold text-zinc-700">{formatPercent(payoffProgress)} paid</span>
              </div>
              <div className="w-full h-3 bg-zinc-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${payoffProgress}%` }}
                />
              </div>
              <div className="flex justify-between mt-1.5 text-[10px] text-zinc-400">
                <span>{p.purchaseDate.slice(0, 4)}</span>
                <span>{Number(p.purchaseDate.slice(0, 4)) + p.loanTerm}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Expenses */}
        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-200 flex items-center gap-2">
            <Wrench className="w-5 h-5 text-zinc-400" />
            <h2 className="text-lg font-bold text-zinc-900">Recent Expenses</h2>
          </div>
          <div className="divide-y divide-zinc-100">
            {p.recentExpenses.map((exp) => (
              <div key={exp.id} className="px-6 py-4 flex items-center justify-between hover:bg-zinc-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center flex-shrink-0">
                    <Wrench className="w-4 h-4 text-zinc-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-zinc-900">{exp.description}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-zinc-400">
                        {new Date(exp.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                      <span className={clsx('text-[10px] font-semibold px-1.5 py-0.5 rounded', expenseCategoryColor[exp.category] || 'bg-zinc-100 text-zinc-600')}>
                        {exp.category}
                      </span>
                    </div>
                  </div>
                </div>
                <span className="text-sm font-bold text-red-600">-{formatCurrency(exp.amount)}</span>
              </div>
            ))}
          </div>
          <div className="px-6 py-3 bg-zinc-50 border-t border-zinc-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 uppercase">Total Recent</span>
            <span className="text-sm font-bold text-red-600">
              -{formatCurrency(p.recentExpenses.reduce((s, e) => s + e.amount, 0))}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
