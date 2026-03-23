import axios from "axios";
import type {
  Property, PropertyCreate, Unit, UnitCreate, Tenant, TenantCreate,
  Lease, LeaseCreate, Payment, PaymentCreate, PaymentSummary,
  MaintenanceRequest, MaintenanceRequestCreate, Contractor, Document,
  Conversation, Message, DashboardData, IncomeBreakdown, ExpenseBreakdown,
  LoginRequest, LoginResponse,
} from "@/types";

const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("rd_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("rd_token");
      localStorage.removeItem("rd_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>("/auth/login", data).then((r) => r.data),
  register: (data: LoginRequest & { first_name: string; last_name: string }) =>
    api.post<LoginResponse>("/auth/register", data).then((r) => r.data),
};

export const propertiesApi = {
  list: () => api.get<Property[]>("/properties").then((r) => r.data),
  get: (id: string) => api.get<Property>(`/properties/${id}`).then((r) => r.data),
  create: (data: PropertyCreate) => api.post<Property>("/properties", data).then((r) => r.data),
  update: (id: string, data: Partial<PropertyCreate>) => api.put<Property>(`/properties/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/properties/${id}`),
  financials: (id: string) => api.get(`/properties/${id}/financials`).then((r) => r.data),
};

export const unitsApi = {
  list: (propertyId: string) => api.get<Unit[]>(`/properties/${propertyId}/units`).then((r) => r.data),
  get: (id: string) => api.get<Unit>(`/units/${id}`).then((r) => r.data),
  create: (propertyId: string, data: UnitCreate) => api.post<Unit>(`/properties/${propertyId}/units`, data).then((r) => r.data),
  update: (id: string, data: Partial<UnitCreate>) => api.put<Unit>(`/units/${id}`, data).then((r) => r.data),
};

export const tenantsApi = {
  list: () => api.get<Tenant[]>("/tenants").then((r) => r.data),
  get: (id: string) => api.get<Tenant>(`/tenants/${id}`).then((r) => r.data),
  create: (data: TenantCreate) => api.post<Tenant>("/tenants", data).then((r) => r.data),
  update: (id: string, data: Partial<TenantCreate>) => api.put<Tenant>(`/tenants/${id}`, data).then((r) => r.data),
  payments: (id: string) => api.get<Payment[]>(`/tenants/${id}/payments`).then((r) => r.data),
};

export const leasesApi = {
  list: (params?: { status?: string }) => api.get<Lease[]>("/leases", { params }).then((r) => r.data),
  get: (id: string) => api.get<Lease>(`/leases/${id}`).then((r) => r.data),
  create: (data: LeaseCreate) => api.post<Lease>("/leases", data).then((r) => r.data),
  update: (id: string, data: Partial<LeaseCreate>) => api.put<Lease>(`/leases/${id}`, data).then((r) => r.data),
};

export const paymentsApi = {
  list: (params?: { status?: string }) => api.get<Payment[]>("/payments", { params }).then((r) => r.data),
  create: (data: PaymentCreate) => api.post<Payment>("/payments", data).then((r) => r.data),
  get: (id: string) => api.get<Payment>(`/payments/${id}`).then((r) => r.data),
  summary: () => api.get<PaymentSummary>("/payments/summary").then((r) => r.data),
  aging: () => api.get("/payments/aging").then((r) => r.data),
};

export const maintenanceApi = {
  list: (params?: { status?: string; urgency?: string }) =>
    api.get<MaintenanceRequest[]>("/maintenance", { params }).then((r) => r.data),
  get: (id: string) => api.get<MaintenanceRequest>(`/maintenance/${id}`).then((r) => r.data),
  create: (data: MaintenanceRequestCreate) =>
    api.post<MaintenanceRequest>("/maintenance", data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    api.put<MaintenanceRequest>(`/maintenance/${id}`, data).then((r) => r.data),
  diagnose: (id: string) => api.post(`/maintenance/${id}/diagnose`).then((r) => r.data),
  approve: (id: string, quoteId: string) =>
    api.post(`/maintenance/${id}/approve`, { quote_id: quoteId }).then((r) => r.data),
  complete: (id: string, actualCost?: number) =>
    api.post(`/maintenance/${id}/complete`, { actual_cost: actualCost }).then((r) => r.data),
};

export const contractorsApi = {
  list: () => api.get<Contractor[]>("/contractors").then((r) => r.data),
  create: (data: Record<string, unknown>) => api.post<Contractor>("/contractors", data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) => api.put<Contractor>(`/contractors/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/contractors/${id}`),
};

export const documentsApi = {
  list: (params?: { doc_type?: string; property_id?: string }) =>
    api.get<Document[]>("/documents", { params }).then((r) => r.data),
  get: (id: string) => api.get<Document>(`/documents/${id}`).then((r) => r.data),
  upload: (formData: FormData) =>
    api.post<Document>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  delete: (id: string) => api.delete(`/documents/${id}`),
  analyze: (id: string) => api.post(`/documents/${id}/analyze`).then((r) => r.data),
};

export const chatApi = {
  send: (tenantId: string, message: string) =>
    api.post("/ai/chat", { tenant_id: tenantId, message }).then((r) => r.data),
  conversations: (tenantId: string) =>
    api.get<{ conversation: Conversation; messages: Message[] }>(`/ai/conversations/${tenantId}`).then((r) => r.data),
  escalations: () => api.get("/ai/escalations").then((r) => r.data),
  resolve: (id: string) => api.post(`/ai/escalations/${id}/resolve`).then((r) => r.data),
};

export const financialsApi = {
  dashboard: () => api.get<DashboardData>("/financials/dashboard").then((r) => r.data),
  income: () => api.get<IncomeBreakdown[]>("/financials/income").then((r) => r.data),
  expenses: () => api.get<ExpenseBreakdown[]>("/financials/expenses").then((r) => r.data),
  createExpense: (data: Record<string, unknown>) =>
    api.post("/financials/expenses", data).then((r) => r.data),
};

export const onboardingApi = {
  status: () => api.get("/onboarding/status").then((r) => r.data),
  savePreferences: (data: Record<string, unknown>) =>
    api.post("/onboarding/preferences", data).then((r) => r.data),
  recommendedMarkets: () =>
    api.get("/onboarding/recommended-markets").then((r) => r.data),
  createAlerts: () =>
    api.post("/onboarding/create-alerts").then((r) => r.data),
};

export const apiKeysApi = {
  list: () => api.get("/api-keys").then((r) => r.data),
  create: (data: { name?: string; rate_limit_per_hour?: number; expires_at?: string }) =>
    api.post("/api-keys", data).then((r) => r.data),
  revoke: (id: string) => api.delete(`/api-keys/${id}`),
  usage: (id: string) => api.get(`/api-keys/${id}/usage`).then((r) => r.data),
};

export const adminApi = {
  stats: () => api.get("/admin/stats").then((r) => r.data),
  users: (params?: Record<string, unknown>) =>
    api.get("/admin/users", { params }).then((r) => r.data),
  updateUser: (id: string, data: Record<string, unknown>) =>
    api.put(`/admin/users/${id}`, data).then((r) => r.data),
  userActivity: (id: string, limit?: number) =>
    api.get(`/admin/users/${id}/activity`, { params: { limit } }).then((r) => r.data),
  scrapersStatus: () => api.get("/admin/scrapers/status").then((r) => r.data),
  triggerScraper: (source: string, market?: string) =>
    api.post(`/admin/scrapers/${source}/run`, null, { params: { market } }).then((r) => r.data),
  scraperLogs: (params?: Record<string, unknown>) =>
    api.get("/admin/scrapers/logs", { params }).then((r) => r.data),
  engagement: () => api.get("/admin/analytics/engagement").then((r) => r.data),
  conversion: () => api.get("/admin/analytics/conversion").then((r) => r.data),
  popularMarkets: (limit?: number) =>
    api.get("/admin/analytics/popular-markets", { params: { limit } }).then((r) => r.data),
  reanalyzeProperties: () =>
    api.post("/admin/properties/reanalyze").then((r) => r.data),
};

export default api;
