// ============================================================
// RealDeal AI — Property Management Types
// ============================================================

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  company_name?: string;
  plan_tier: "starter" | "growth" | "pro";
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ---- Property ----
export interface Property {
  id: string;
  name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
  property_type: "sfh" | "multi" | "condo" | "townhouse";
  total_units: number;
  purchase_price?: number;
  current_value?: number;
  mortgage_payment?: number;
  insurance_cost?: number;
  tax_annual?: number;
  is_active: boolean;
  created_at: string;
  units?: Unit[];
}

export interface PropertyCreate {
  name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
  property_type: string;
  total_units: number;
  purchase_price?: number;
  current_value?: number;
  mortgage_payment?: number;
  insurance_cost?: number;
  tax_annual?: number;
}

// ---- Unit ----
export interface Unit {
  id: string;
  property_id: string;
  unit_number: string;
  bedrooms?: number;
  bathrooms?: number;
  sqft?: number;
  market_rent?: number;
  status: "vacant" | "occupied" | "maintenance" | "turnover";
  created_at: string;
}

export interface UnitCreate {
  unit_number: string;
  bedrooms?: number;
  bathrooms?: number;
  sqft?: number;
  market_rent?: number;
}

// ---- Tenant ----
export interface Tenant {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone: string;
  is_active: boolean;
  portal_enabled: boolean;
  preferred_language: string;
  unit_number?: string;
  property_name?: string;
  rent_amount?: number;
  payment_status?: string;
  created_at: string;
}

export interface TenantCreate {
  first_name: string;
  last_name: string;
  email?: string;
  phone: string;
  preferred_language?: string;
}

// ---- Lease ----
export interface Lease {
  id: string;
  unit_id: string;
  tenant_id: string;
  rent_amount: number;
  deposit_amount?: number;
  start_date: string;
  end_date?: string;
  rent_due_day: number;
  late_fee_amount?: number;
  late_fee_grace_days: number;
  lease_type: "fixed" | "month_to_month";
  status: "active" | "expired" | "terminated";
  created_at: string;
}

export interface LeaseCreate {
  unit_id: string;
  tenant_id: string;
  rent_amount: number;
  deposit_amount?: number;
  start_date: string;
  end_date?: string;
  rent_due_day?: number;
  late_fee_amount?: number;
  late_fee_grace_days?: number;
  lease_type?: string;
}

// ---- Payment ----
export interface Payment {
  id: string;
  lease_id: string;
  tenant_id: string;
  amount: number;
  payment_type: "rent" | "late_fee" | "deposit" | "other";
  payment_method?: "stripe" | "ach" | "zelle" | "cash" | "check";
  status: "pending" | "completed" | "failed" | "refunded";
  stripe_payment_id?: string;
  due_date: string;
  paid_date?: string;
  notes?: string;
  tenant_name?: string;
  unit_number?: string;
  created_at: string;
}

export interface PaymentCreate {
  lease_id: string;
  amount: number;
  payment_type: string;
  payment_method: string;
  due_date: string;
  notes?: string;
}

export interface PaymentSummary {
  total_collected: number;
  total_outstanding: number;
  total_late: number;
  collection_rate: number;
}

// ---- Maintenance ----
export interface MaintenanceRequest {
  id: string;
  unit_id: string;
  tenant_id?: string;
  title: string;
  description: string;
  category?: "plumbing" | "electrical" | "hvac" | "appliance" | "structural" | "pest" | "other";
  urgency: "emergency" | "urgent" | "routine";
  status: "new" | "diagnosed" | "quoting" | "approved" | "scheduled" | "in_progress" | "completed" | "cancelled";
  ai_diagnosis?: AIDiagnosis;
  ai_confidence?: number;
  estimated_cost_low?: number;
  estimated_cost_high?: number;
  actual_cost?: number;
  scheduled_date?: string;
  completed_date?: string;
  tenant_rating?: number;
  tenant_feedback?: string;
  photos?: MaintenancePhoto[];
  quotes?: Quote[];
  unit_number?: string;
  property_name?: string;
  tenant_name?: string;
  created_at: string;
}

export interface MaintenanceRequestCreate {
  unit_id: string;
  tenant_id?: string;
  title: string;
  description: string;
  category?: string;
  urgency?: string;
  photos?: string[]; // base64
}

export interface MaintenancePhoto {
  id: string;
  s3_key: string;
  ai_analysis?: Record<string, unknown>;
  uploaded_by: string;
  created_at: string;
}

export interface AIDiagnosis {
  category: string;
  severity: number;
  urgency: string;
  description: string;
  possible_causes: string[];
  recommended_action: string;
  trade_needed: string;
  estimated_cost_low: number;
  estimated_cost_high: number;
  confidence: number;
}

// ---- Contractor ----
export interface Contractor {
  id: string;
  company_name: string;
  contact_name?: string;
  phone: string;
  email?: string;
  trades: string[];
  avg_rating: number;
  total_jobs: number;
  is_active: boolean;
  created_at: string;
}

// ---- Quote ----
export interface Quote {
  id: string;
  request_id: string;
  contractor_id: string;
  contractor_name?: string;
  amount: number;
  description?: string;
  estimated_hours?: number;
  available_date?: string;
  status: "pending" | "accepted" | "rejected" | "expired";
  created_at: string;
}

// ---- Document ----
export interface Document {
  id: string;
  property_id?: string;
  unit_id?: string;
  tenant_id?: string;
  doc_type: "lease" | "inspection" | "contract" | "notice" | "receipt" | "insurance" | "other";
  filename: string;
  s3_key: string;
  file_size?: number;
  mime_type?: string;
  ai_analysis?: Record<string, unknown>;
  tags?: string[];
  created_at: string;
}

// ---- Conversation / Message ----
export interface Conversation {
  id: string;
  tenant_id: string;
  tenant_name?: string;
  channel: "sms" | "email" | "web" | "whatsapp";
  status: "active" | "escalated" | "resolved";
  last_message?: string;
  last_message_at?: string;
  unread_count?: number;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: "tenant" | "ai" | "landlord";
  content: string;
  intent?: string;
  confidence?: number;
  created_at: string;
}

// ---- Financials ----
export interface DashboardData {
  total_units: number;
  occupied_units: number;
  occupancy_rate: number;
  total_collected: number;
  total_outstanding: number;
  noi: number;
  cash_flow: number;
  cap_rate: number;
  maintenance_spend: number;
  insights: Insight[];
}

export interface Insight {
  type: "warning" | "alert" | "info" | "success";
  title: string;
  body: string;
  action?: string;
}

export interface IncomeBreakdown {
  property_id: string;
  property_name: string;
  income: number;
  expenses: number;
  noi: number;
}

export interface ExpenseBreakdown {
  category: string;
  amount: number;
  percentage: number;
}

// ---- Notification ----
export interface Notification {
  id: string;
  title: string;
  body: string;
  category?: string;
  is_read: boolean;
  action_url?: string;
  created_at: string;
}

// ---- Activity Feed ----
export interface ActivityItem {
  id: string;
  action: string;
  detail: string;
  timestamp: string;
  type: "payment" | "maintenance" | "message" | "lease" | "system";
}

// ---- Generic ----
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ColumnDef<T> {
  key: keyof T | string;
  header: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  width?: string;
  align?: "left" | "center" | "right";
}
