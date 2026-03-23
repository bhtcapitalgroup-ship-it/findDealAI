import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Building2, MapPin, ArrowRight, TrendingUp, Home, Users,
  DollarSign, Percent, ChevronRight, ChevronLeft, Check, X,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import clsx from 'clsx';
import { formatCurrency, formatPercent } from '@/lib/utils';
import Badge from '../components/Badge';
import { propertiesApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface UnitData {
  unitNumber: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  monthlyRent: number;
  status: 'occupied' | 'vacant';
}

interface PropertyData {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  type: 'Multi-Family' | 'Townhouse' | 'Condo' | 'Single Family' | 'Commercial';
  units: UnitData[];
  purchasePrice: number;
  currentValue: number;
  monthlyMortgage: number;
  annualTax: number;
  annualInsurance: number;
  monthlyHOA: number;
  monthlyManagement: number;
  monthlyMaintenance: number;
  lender: string;
  loanAmount: number;
  interestRate: number;
  loanTerm: number;
  monthlyEscrow: number;
  purchaseDate: string;
  yearBuilt: number;
  closingCosts: number;
  rehabCosts: number;
  downPayment: number;
}

// ---------------------------------------------------------------------------
// Mock Data (consistent with spec)
// ---------------------------------------------------------------------------
const mockProperties: PropertyData[] = [
  {
    id: '1',
    name: 'Maple Street Apartments',
    address: '742 Maple St',
    city: 'Portland',
    state: 'OR',
    zip: '97201',
    type: 'Multi-Family',
    purchasePrice: 2_400_000,
    currentValue: 2_800_000,
    monthlyMortgage: 9_800,
    annualTax: 28_000,
    annualInsurance: 10_200,
    monthlyHOA: 0,
    monthlyManagement: 1_970,
    monthlyMaintenance: 800,
    lender: 'Pacific Northwest Bank',
    loanAmount: 1_920_000,
    interestRate: 6.25,
    loanTerm: 30,
    monthlyEscrow: 450,
    purchaseDate: '2021-06-15',
    yearBuilt: 1998,
    closingCosts: 36_000,
    rehabCosts: 85_000,
    downPayment: 480_000,
    units: [
      { unitNumber: '1A', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied' },
      { unitNumber: '1B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied' },
      { unitNumber: '2A', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_750, status: 'occupied' },
      { unitNumber: '2B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_750, status: 'vacant' },
      { unitNumber: '3A', bedrooms: 3, bathrooms: 2, sqft: 1_100, monthlyRent: 2_100, status: 'occupied' },
      { unitNumber: '3B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied' },
      { unitNumber: '4A', bedrooms: 2, bathrooms: 2, sqft: 950, monthlyRent: 1_800, status: 'occupied' },
      { unitNumber: '4B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied' },
      { unitNumber: '5A', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied' },
      { unitNumber: '5B', bedrooms: 1, bathrooms: 1, sqft: 650, monthlyRent: 1_350, status: 'occupied' },
      { unitNumber: '6A', bedrooms: 3, bathrooms: 2, sqft: 1_100, monthlyRent: 2_100, status: 'occupied' },
      { unitNumber: '6B', bedrooms: 2, bathrooms: 1, sqft: 850, monthlyRent: 1_600, status: 'occupied' },
    ],
  },
  {
    id: '2',
    name: 'Oak Park Townhomes',
    address: '1200 Oak Park Dr',
    city: 'Portland',
    state: 'OR',
    zip: '97205',
    type: 'Townhouse',
    purchasePrice: 1_600_000,
    currentValue: 1_900_000,
    monthlyMortgage: 6_500,
    annualTax: 19_000,
    annualInsurance: 7_200,
    monthlyHOA: 200,
    monthlyManagement: 1_430,
    monthlyMaintenance: 550,
    lender: 'Columbia Credit Union',
    loanAmount: 1_280_000,
    interestRate: 5.875,
    loanTerm: 30,
    monthlyEscrow: 350,
    purchaseDate: '2022-03-10',
    yearBuilt: 2005,
    closingCosts: 24_000,
    rehabCosts: 40_000,
    downPayment: 320_000,
    units: [
      { unitNumber: 'A', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied' },
      { unitNumber: 'B', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied' },
      { unitNumber: 'C', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'occupied' },
      { unitNumber: 'D', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'vacant' },
      { unitNumber: 'E', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 2_100, status: 'occupied' },
      { unitNumber: 'F', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_650, status: 'occupied' },
      { unitNumber: 'G', bedrooms: 3, bathrooms: 2.5, sqft: 1_450, monthlyRent: 1_550, status: 'occupied' },
      { unitNumber: 'H', bedrooms: 2, bathrooms: 2, sqft: 1_200, monthlyRent: 1_500, status: 'occupied' },
    ],
  },
  {
    id: '3',
    name: 'Cedar Heights Condo',
    address: '890 Cedar Heights Way',
    city: 'Lake Oswego',
    state: 'OR',
    zip: '97034',
    type: 'Condo',
    purchasePrice: 850_000,
    currentValue: 980_000,
    monthlyMortgage: 3_400,
    annualTax: 10_500,
    annualInsurance: 4_200,
    monthlyHOA: 450,
    monthlyManagement: 880,
    monthlyMaintenance: 300,
    lender: 'Oregon First Mortgage',
    loanAmount: 680_000,
    interestRate: 6.0,
    loanTerm: 30,
    monthlyEscrow: 250,
    purchaseDate: '2023-01-20',
    yearBuilt: 2012,
    closingCosts: 12_750,
    rehabCosts: 15_000,
    downPayment: 170_000,
    units: [
      { unitNumber: '101', bedrooms: 2, bathrooms: 2, sqft: 1_050, monthlyRent: 2_200, status: 'occupied' },
      { unitNumber: '102', bedrooms: 2, bathrooms: 2, sqft: 1_050, monthlyRent: 2_200, status: 'occupied' },
      { unitNumber: '201', bedrooms: 3, bathrooms: 2, sqft: 1_300, monthlyRent: 2_400, status: 'occupied' },
      { unitNumber: '202', bedrooms: 1, bathrooms: 1, sqft: 750, monthlyRent: 2_000, status: 'occupied' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------
function totalRent(p: PropertyData) {
  return p.units.reduce((s, u) => s + u.monthlyRent, 0);
}
function occupiedCount(p: PropertyData) {
  return p.units.filter((u) => u.status === 'occupied').length;
}
function monthlyExpenses(p: PropertyData) {
  return p.monthlyMortgage + p.annualTax / 12 + p.annualInsurance / 12 + p.monthlyHOA + p.monthlyManagement + p.monthlyMaintenance;
}
function monthlyCashFlow(p: PropertyData) {
  return totalRent(p) - monthlyExpenses(p);
}
function annualNOI(p: PropertyData) {
  const opex = (p.annualTax + p.annualInsurance + p.monthlyHOA * 12 + p.monthlyManagement * 12 + p.monthlyMaintenance * 12);
  return totalRent(p) * 12 - opex;
}
function capRate(p: PropertyData) {
  return (annualNOI(p) / p.currentValue) * 100;
}
function cashOnCash(p: PropertyData) {
  const totalInvested = p.downPayment + p.closingCosts + p.rehabCosts;
  const annualCF = monthlyCashFlow(p) * 12;
  return totalInvested > 0 ? (annualCF / totalInvested) * 100 : 0;
}

// ---------------------------------------------------------------------------
// Amortization helper
// ---------------------------------------------------------------------------
function calcMonthlyPayment(principal: number, annualRate: number, termYears: number) {
  if (principal <= 0 || annualRate <= 0 || termYears <= 0) return 0;
  const r = annualRate / 100 / 12;
  const n = termYears * 12;
  return (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
}

// ---------------------------------------------------------------------------
// Small reusable pieces
// ---------------------------------------------------------------------------
function MetricBadge({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center px-3 py-2 rounded-lg bg-zinc-50 border border-zinc-100 min-w-[90px]">
      <span className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">{label}</span>
      <span className={clsx('text-sm font-bold mt-0.5', color || 'text-zinc-900')}>{value}</span>
    </div>
  );
}

const typeBadgeVariant: Record<string, 'info' | 'purple' | 'warning' | 'success' | 'neutral'> = {
  'Multi-Family': 'info',
  Townhouse: 'purple',
  Condo: 'warning',
  'Single Family': 'success',
  Commercial: 'neutral',
};

// ---------------------------------------------------------------------------
// Add Property Modal
// ---------------------------------------------------------------------------
const STEPS = ['Property Details', 'Purchase & Costs', 'Mortgage', 'Recurring Costs', 'Rental Income'];

interface FormUnit {
  unitNumber: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  monthlyRent: number;
  status: 'occupied' | 'vacant';
}

const emptyUnit: FormUnit = { unitNumber: '', bedrooms: 1, bathrooms: 1, sqft: 0, monthlyRent: 0, status: 'occupied' };

function AddPropertyModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState(0);
  const [showClosingDetails, setShowClosingDetails] = useState(false);

  // Tab 1
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [zip, setZip] = useState('');
  const [propertyType, setPropertyType] = useState('Multi-Family');
  const [numUnits, setNumUnits] = useState(1);
  const [yearBuilt, setYearBuilt] = useState('');

  // Tab 2
  const [purchasePrice, setPurchasePrice] = useState(0);
  const [purchaseDate, setPurchaseDate] = useState('');
  const [currentValue, setCurrentValue] = useState(0);
  const [appraisalFee, setAppraisalFee] = useState(0);
  const [inspectionFee, setInspectionFee] = useState(0);
  const [titleInsurance, setTitleInsurance] = useState(0);
  const [escrowFees, setEscrowFees] = useState(0);
  const [loanOrigination, setLoanOrigination] = useState(0);
  const [surveyFee, setSurveyFee] = useState(0);
  const [insurancePrepaid, setInsurancePrepaid] = useState(0);
  const [taxesPrepaid, setTaxesPrepaid] = useState(0);
  const [otherClosing, setOtherClosing] = useState(0);
  const [rehabCostsForm, setRehabCostsForm] = useState(0);

  // Tab 3
  const [lenderName, setLenderName] = useState('');
  const [loanAmount, setLoanAmount] = useState(0);
  const [interestRate, setInterestRate] = useState(0);
  const [loanTerm, setLoanTerm] = useState(30);
  const [monthlyEscrow, setMonthlyEscrow] = useState(0);
  const [mortgageStart, setMortgageStart] = useState('');

  // Tab 4
  const [annualTax, setAnnualTax] = useState(0);
  const [annualInsurance, setAnnualInsurance] = useState(0);
  const [monthlyHOA, setMonthlyHOA] = useState(0);
  const [monthlyMgmt, setMonthlyMgmt] = useState(0);
  const [monthlyMaint, setMonthlyMaint] = useState(0);

  // Tab 5
  const [formUnits, setFormUnits] = useState<FormUnit[]>([{ ...emptyUnit }]);

  // Derived
  const totalClosing = appraisalFee + inspectionFee + titleInsurance + escrowFees + loanOrigination + surveyFee + insurancePrepaid + taxesPrepaid + otherClosing;
  const downPayment = purchasePrice - loanAmount;
  const totalCashInvested = (downPayment > 0 ? downPayment : 0) + totalClosing + rehabCostsForm;
  const calculatedPayment = calcMonthlyPayment(loanAmount, interestRate, loanTerm);
  const totalMonthlyRent = formUnits.reduce((s, u) => s + u.monthlyRent, 0);
  const totalMonthlyExpenses = calculatedPayment + annualTax / 12 + annualInsurance / 12 + monthlyHOA + monthlyMgmt + monthlyMaint;
  const formCashFlow = totalMonthlyRent - totalMonthlyExpenses;
  const formNOI = totalMonthlyRent * 12 - (annualTax + annualInsurance + monthlyHOA * 12 + monthlyMgmt * 12 + monthlyMaint * 12);
  const formCapRate = currentValue > 0 ? (formNOI / currentValue) * 100 : 0;
  const formCoC = totalCashInvested > 0 ? (formCashFlow * 12 / totalCashInvested) * 100 : 0;

  function addUnit() {
    setFormUnits([...formUnits, { ...emptyUnit }]);
  }
  function removeUnit(i: number) {
    setFormUnits(formUnits.filter((_, idx) => idx !== i));
  }
  function updateUnit(i: number, field: keyof FormUnit, value: string | number) {
    const updated = [...formUnits];
    (updated[i] as unknown as Record<string, unknown>)[field] = value;
    setFormUnits(updated);
  }

  if (!open) return null;

  const inputClass = 'w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white';
  const labelClass = 'block text-xs font-semibold text-zinc-600 mb-1 uppercase tracking-wider';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl mx-4 max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
          <h2 className="text-lg font-bold text-zinc-900">Add Property</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step Indicators */}
        <div className="px-6 py-3 border-b border-zinc-100 bg-zinc-50/50">
          <div className="flex items-center justify-between">
            {STEPS.map((s, i) => (
              <button
                key={s}
                onClick={() => setStep(i)}
                className="flex items-center gap-2 group"
              >
                <div className={clsx(
                  'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all',
                  i < step ? 'bg-emerald-500 text-white' : i === step ? 'bg-blue-600 text-white' : 'bg-zinc-200 text-zinc-500'
                )}>
                  {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span className={clsx(
                  'text-xs font-medium hidden sm:inline transition-colors',
                  i === step ? 'text-blue-600' : 'text-zinc-400 group-hover:text-zinc-600'
                )}>{s}</span>
                {i < STEPS.length - 1 && <ChevronRight className="w-3.5 h-3.5 text-zinc-300 ml-1" />}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Step 1: Property Details */}
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <label className={labelClass}>Property Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Maple Street Apartments" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Street Address</label>
                <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="742 Maple St" className={inputClass} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>City</label>
                  <input type="text" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Portland" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>State</label>
                  <input type="text" value={state} onChange={(e) => setState(e.target.value)} placeholder="OR" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Zip</label>
                  <input type="text" value={zip} onChange={(e) => setZip(e.target.value)} placeholder="97201" className={inputClass} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>Property Type</label>
                  <select value={propertyType} onChange={(e) => setPropertyType(e.target.value)} className={inputClass}>
                    <option>Single Family</option>
                    <option>Multi-Family</option>
                    <option>Townhouse</option>
                    <option>Condo</option>
                    <option>Commercial</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Number of Units</label>
                  <input type="number" min={1} value={numUnits} onChange={(e) => setNumUnits(Number(e.target.value))} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Year Built (optional)</label>
                  <input type="text" value={yearBuilt} onChange={(e) => setYearBuilt(e.target.value)} placeholder="2005" className={inputClass} />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Purchase & Costs */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>Purchase Price</label>
                  <input type="number" value={purchasePrice || ''} onChange={(e) => setPurchasePrice(Number(e.target.value))} placeholder="2,400,000" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Purchase Date</label>
                  <input type="date" value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Current Market Value</label>
                  <input type="number" value={currentValue || ''} onChange={(e) => setCurrentValue(Number(e.target.value))} placeholder="2,800,000" className={inputClass} />
                </div>
              </div>

              {/* Closing Costs */}
              <div className="border border-zinc-200 rounded-xl overflow-hidden">
                <button onClick={() => setShowClosingDetails(!showClosingDetails)} className="w-full flex items-center justify-between px-4 py-3 bg-zinc-50 hover:bg-zinc-100 transition-colors">
                  <span className="text-sm font-semibold text-zinc-700">Closing Costs</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-zinc-900">{formatCurrency(totalClosing)}</span>
                    {showClosingDetails ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </div>
                </button>
                {showClosingDetails && (
                  <div className="p-4 grid grid-cols-3 gap-3 border-t border-zinc-200">
                    {([
                      ['Appraisal Fee', appraisalFee, setAppraisalFee],
                      ['Inspection Fee', inspectionFee, setInspectionFee],
                      ['Title Insurance', titleInsurance, setTitleInsurance],
                      ['Escrow Fees', escrowFees, setEscrowFees],
                      ['Loan Origination', loanOrigination, setLoanOrigination],
                      ['Survey', surveyFee, setSurveyFee],
                      ['Insurance Prepaid', insurancePrepaid, setInsurancePrepaid],
                      ['Taxes Prepaid', taxesPrepaid, setTaxesPrepaid],
                      ['Other', otherClosing, setOtherClosing],
                    ] as [string, number, React.Dispatch<React.SetStateAction<number>>][]).map(([lbl, val, setter]) => (
                      <div key={lbl}>
                        <label className={labelClass}>{lbl}</label>
                        <input type="number" value={val || ''} onChange={(e) => setter(Number(e.target.value))} className={inputClass} />
                      </div>
                    ))}
                    <div className="col-span-3 pt-2 border-t border-zinc-100 flex justify-between items-center">
                      <span className="text-xs font-semibold text-zinc-500 uppercase">Total Closing Costs</span>
                      <span className="text-sm font-bold text-zinc-900">{formatCurrency(totalClosing)}</span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className={labelClass}>Rehab / Renovation Costs</label>
                <input type="number" value={rehabCostsForm || ''} onChange={(e) => setRehabCostsForm(Number(e.target.value))} className={inputClass} />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
                <span className="text-sm font-semibold text-blue-800">Total Cash Invested</span>
                <span className="text-lg font-bold text-blue-900">{formatCurrency(totalCashInvested)}</span>
              </div>
            </div>
          )}

          {/* Step 3: Mortgage */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className={labelClass}>Lender Name</label>
                <input type="text" value={lenderName} onChange={(e) => setLenderName(e.target.value)} placeholder="Pacific Northwest Bank" className={inputClass} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>Loan Amount</label>
                  <input type="number" value={loanAmount || ''} onChange={(e) => setLoanAmount(Number(e.target.value))} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Interest Rate (%)</label>
                  <input type="number" step="0.125" value={interestRate || ''} onChange={(e) => setInterestRate(Number(e.target.value))} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Loan Term</label>
                  <select value={loanTerm} onChange={(e) => setLoanTerm(Number(e.target.value))} className={inputClass}>
                    <option value={15}>15 years</option>
                    <option value={20}>20 years</option>
                    <option value={30}>30 years</option>
                  </select>
                </div>
              </div>

              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
                <span className="text-sm font-semibold text-emerald-800">Monthly Payment (P&I)</span>
                <span className="text-lg font-bold text-emerald-900">{formatCurrency(Math.round(calculatedPayment))}</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Monthly Escrow</label>
                  <input type="number" value={monthlyEscrow || ''} onChange={(e) => setMonthlyEscrow(Number(e.target.value))} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Start Date</label>
                  <input type="date" value={mortgageStart} onChange={(e) => setMortgageStart(e.target.value)} className={inputClass} />
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Recurring Costs */}
          {step === 3 && (
            <div className="space-y-4">
              {([
                ['Annual Property Tax', annualTax, setAnnualTax, true],
                ['Annual Insurance', annualInsurance, setAnnualInsurance, true],
                ['Monthly HOA', monthlyHOA, setMonthlyHOA, false],
                ['Monthly Property Management', monthlyMgmt, setMonthlyMgmt, false],
                ['Estimated Monthly Maintenance', monthlyMaint, setMonthlyMaint, false],
              ] as [string, number, React.Dispatch<React.SetStateAction<number>>, boolean][]).map(([lbl, val, setter, showMonthly]) => (
                <div key={lbl} className="flex items-center gap-4">
                  <div className="flex-1">
                    <label className={labelClass}>{lbl}</label>
                    <input type="number" value={val || ''} onChange={(e) => setter(Number(e.target.value))} className={inputClass} />
                  </div>
                  {showMonthly && val > 0 && (
                    <div className="pt-5">
                      <span className="text-xs text-zinc-400 font-medium">{formatCurrency(Math.round(val / 12))}/mo</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Step 5: Rental Income */}
          {step === 4 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-zinc-700">Units</span>
                <button onClick={addUnit} className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700">
                  <Plus className="w-3.5 h-3.5" /> Add Unit
                </button>
              </div>
              {formUnits.map((u, i) => (
                <div key={i} className="grid grid-cols-7 gap-2 items-end border border-zinc-200 rounded-lg p-3 bg-zinc-50/50">
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Unit #</label>
                    <input type="text" value={u.unitNumber} onChange={(e) => updateUnit(i, 'unitNumber', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Beds</label>
                    <input type="number" min={0} value={u.bedrooms} onChange={(e) => updateUnit(i, 'bedrooms', Number(e.target.value))} className={inputClass} />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Baths</label>
                    <input type="number" min={0} step={0.5} value={u.bathrooms} onChange={(e) => updateUnit(i, 'bathrooms', Number(e.target.value))} className={inputClass} />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Sqft</label>
                    <input type="number" min={0} value={u.sqft || ''} onChange={(e) => updateUnit(i, 'sqft', Number(e.target.value))} className={inputClass} />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Rent</label>
                    <input type="number" min={0} value={u.monthlyRent || ''} onChange={(e) => updateUnit(i, 'monthlyRent', Number(e.target.value))} className={inputClass} />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase">Status</label>
                    <select value={u.status} onChange={(e) => updateUnit(i, 'status', e.target.value)} className={inputClass}>
                      <option value="occupied">Occupied</option>
                      <option value="vacant">Vacant</option>
                    </select>
                  </div>
                  <div className="flex justify-center pb-1">
                    <button onClick={() => removeUnit(i)} className="text-zinc-300 hover:text-red-500 transition-colors p-1" title="Remove unit">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center justify-between mt-4">
                <span className="text-sm font-semibold text-emerald-800">Total Monthly Rent</span>
                <span className="text-lg font-bold text-emerald-900">{formatCurrency(totalMonthlyRent)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Summary Panel (always visible) */}
        <div className="border-t border-zinc-200 bg-zinc-50 px-6 py-3">
          <div className="grid grid-cols-6 gap-3 text-center">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Monthly Income</div>
              <div className="text-sm font-bold text-zinc-900">{formatCurrency(totalMonthlyRent)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Monthly Expenses</div>
              <div className="text-sm font-bold text-zinc-900">{formatCurrency(Math.round(totalMonthlyExpenses))}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Cash Flow</div>
              <div className={clsx('text-sm font-bold', formCashFlow >= 0 ? 'text-emerald-600' : 'text-red-600')}>{formatCurrency(Math.round(formCashFlow))}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Annual NOI</div>
              <div className="text-sm font-bold text-zinc-900">{formatCurrency(Math.round(formNOI))}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Cap Rate</div>
              <div className="text-sm font-bold text-zinc-900">{formatPercent(formCapRate)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Cash-on-Cash</div>
              <div className="text-sm font-bold text-zinc-900">{formatPercent(formCoC)}</div>
            </div>
          </div>
        </div>

        {/* Footer Nav */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-200">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className={clsx('flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-colors', step === 0 ? 'text-zinc-300 cursor-not-allowed' : 'text-zinc-600 hover:bg-zinc-100')}
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex gap-3">
            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors">
              Cancel
            </button>
            {step < STEPS.length - 1 ? (
              <button onClick={() => setStep(step + 1)} className="flex items-center gap-1.5 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                Next <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button onClick={onClose} className="px-5 py-2 text-sm font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors">
                Add Property
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function Properties() {
  const navigate = useNavigate();
  const [showAdd, setShowAdd] = useState(false);
  const [properties, setProperties] = useState<PropertyData[]>(mockProperties);

  useEffect(() => {
    propertiesApi.list().then((data) => {
      if (Array.isArray(data) && data.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setProperties((data as any[]).map((p: any) => ({
          id: String(p.id),
          name: String(p.name || ''),
          address: String(p.address_line1 || p.address || ''),
          city: String(p.city || ''),
          state: String(p.state || ''),
          zip: String(p.zip_code || p.zip || ''),
          type: (String(p.property_type || p.type || 'Multi-Family') as PropertyData['type']),
          purchasePrice: Number(p.purchase_price || p.purchasePrice || 0),
          currentValue: Number(p.current_value || p.currentValue || 0),
          monthlyMortgage: Number(p.monthly_mortgage || p.monthlyMortgage || 0),
          annualTax: Number(p.annual_tax || p.annualTax || 0),
          annualInsurance: Number(p.annual_insurance || p.annualInsurance || 0),
          monthlyHOA: Number(p.monthly_hoa || p.monthlyHOA || 0),
          monthlyManagement: Number(p.monthly_management || p.monthlyManagement || 0),
          monthlyMaintenance: Number(p.monthly_maintenance || p.monthlyMaintenance || 0),
          lender: String(p.lender || ''),
          loanAmount: Number(p.loan_amount || p.loanAmount || 0),
          interestRate: Number(p.interest_rate || p.interestRate || 0),
          loanTerm: Number(p.loan_term || p.loanTerm || 30),
          monthlyEscrow: Number(p.monthly_escrow || p.monthlyEscrow || 0),
          purchaseDate: String(p.purchase_date || p.purchaseDate || ''),
          yearBuilt: Number(p.year_built || p.yearBuilt || 0),
          closingCosts: Number(p.closing_costs || p.closingCosts || 0),
          rehabCosts: Number(p.rehab_costs || p.rehabCosts || 0),
          downPayment: Number(p.down_payment || p.downPayment || 0),
          units: Array.isArray(p.units) ? (p.units as any[]).map((u: any) => ({
            unitNumber: String(u.unit_number || u.unitNumber || ''),
            bedrooms: Number(u.bedrooms || 0),
            bathrooms: Number(u.bathrooms || 0),
            sqft: Number(u.sqft || u.square_feet || 0),
            monthlyRent: Number(u.monthly_rent || u.monthlyRent || 0),
            status: (String(u.status || 'vacant') as 'occupied' | 'vacant'),
          })) : [],
        })));
      }
    }).catch(() => {}); // silently fall back to mock data
  }, []);

  // Portfolio totals
  const portfolio = useMemo(() => {
    const totalUnits = properties.reduce((s, p) => s + p.units.length, 0);
    const totalOccupied = properties.reduce((s, p) => s + occupiedCount(p), 0);
    const totalMonthlyIncome = properties.reduce((s, p) => s + totalRent(p), 0);
    const totalValue = properties.reduce((s, p) => s + p.currentValue, 0);
    return { totalUnits, totalOccupied, totalMonthlyIncome, totalValue, count: properties.length };
  }, [properties]);

  return (
    <div className="min-h-screen bg-zinc-50 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Properties</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage your real estate portfolio</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Property
        </button>
      </div>

      {/* Portfolio Summary Bar */}
      <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
        <div className="grid grid-cols-5 divide-x divide-zinc-200">
          {[
            { label: 'Total Properties', value: String(portfolio.count), icon: Building2 },
            { label: 'Total Units', value: String(portfolio.totalUnits), icon: Home },
            { label: 'Occupied', value: `${portfolio.totalOccupied} (${formatPercent((portfolio.totalOccupied / portfolio.totalUnits) * 100)})`, icon: Users },
            { label: 'Monthly Income', value: formatCurrency(portfolio.totalMonthlyIncome), icon: DollarSign },
            { label: 'Portfolio Value', value: formatCurrency(portfolio.totalValue), icon: TrendingUp },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3 px-5 first:pl-0 last:pr-0">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                <item.icon className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">{item.label}</div>
                <div className="text-xl font-bold text-zinc-900 mt-0.5">{item.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Property Cards */}
      <div className="space-y-4">
        {properties.map((p) => {
          const rent = totalRent(p);
          const occupied = occupiedCount(p);
          const occupancyPct = (occupied / p.units.length) * 100;
          const equity = p.currentValue - p.loanAmount;
          const cf = monthlyCashFlow(p);
          const noi = annualNOI(p);
          const cr = capRate(p);
          const coc = cashOnCash(p);

          return (
            <div
              key={p.id}
              className="bg-white rounded-xl border border-zinc-200 shadow-sm hover:shadow-md hover:border-zinc-300 transition-all"
            >
              <div className="p-5 flex flex-col lg:flex-row lg:items-center gap-5">
                {/* Left: Property Info */}
                <div className="lg:w-[260px] flex-shrink-0 space-y-3">
                  <div>
                    <h3 className="text-lg font-bold text-zinc-900">{p.name}</h3>
                    <div className="flex items-center gap-1 mt-1 text-sm text-zinc-500">
                      <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                      {p.address}, {p.city}, {p.state} {p.zip}
                    </div>
                  </div>
                  <Badge variant={typeBadgeVariant[p.type] || 'neutral'}>{p.type}</Badge>

                  {/* Occupancy Bar */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-zinc-500 font-medium">Occupancy</span>
                      <span className="font-bold text-zinc-900">{occupied}/{p.units.length} — {formatPercent(occupancyPct)}</span>
                    </div>
                    <div className="w-full h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div
                        className={clsx('h-full rounded-full transition-all', occupancyPct >= 90 ? 'bg-emerald-500' : occupancyPct >= 70 ? 'bg-amber-500' : 'bg-red-500')}
                        style={{ width: `${occupancyPct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Center: Financial Grid */}
                <div className="flex-1 grid grid-cols-3 gap-x-6 gap-y-3 border-l border-r border-zinc-100 px-6">
                  {[
                    { label: 'Purchase Price', value: formatCurrency(p.purchasePrice) },
                    { label: 'Current Value', value: formatCurrency(p.currentValue) },
                    { label: 'Equity', value: formatCurrency(equity), color: 'text-emerald-600' },
                    { label: 'Monthly Rent', value: formatCurrency(rent) },
                    { label: 'Monthly Mortgage', value: formatCurrency(p.monthlyMortgage) },
                    { label: 'Monthly Cash Flow', value: formatCurrency(Math.round(cf)), color: cf >= 0 ? 'text-emerald-600' : 'text-red-600' },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">{item.label}</div>
                      <div className={clsx('text-base font-bold mt-0.5', item.color || 'text-zinc-900')}>{item.value}</div>
                    </div>
                  ))}
                </div>

                {/* Right: Key Metrics */}
                <div className="flex flex-row lg:flex-col gap-2 lg:w-[200px] flex-shrink-0">
                  <MetricBadge label="NOI" value={formatCurrency(Math.round(noi))} />
                  <MetricBadge label="Cap Rate" value={formatPercent(cr)} />
                  <MetricBadge label="Cash-on-Cash" value={formatPercent(coc)} />
                  <button
                    onClick={() => navigate(`/properties/${p.id}`)}
                    className="flex items-center justify-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors mt-1"
                  >
                    View Details <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Property Modal */}
      <AddPropertyModal open={showAdd} onClose={() => setShowAdd(false)} />
    </div>
  );
}
