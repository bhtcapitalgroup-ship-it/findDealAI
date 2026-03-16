# RealDeal AI — UX Flows

---

## 1. Landlord Onboarding

```
┌─────────────────────────────────────────────────────────┐
│                    SIGN UP                               │
│  Email + Password  ──or──  Google OAuth                  │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│               ADD FIRST PROPERTY                         │
│  Address │ Units │ Type (SFH/Multi/Condo)                │
│  [Import from spreadsheet] or [Add manually]             │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 ADD UNITS                                 │
│  Unit # │ Bedrooms │ Rent │ Status (Occupied/Vacant)     │
│  ┌──────────────────────────────────┐                    │
│  │ Bulk import via CSV supported    │                    │
│  └──────────────────────────────────┘                    │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                ADD TENANTS                                │
│  Name │ Email │ Phone │ Unit │ Lease Start │ Lease End   │
│  [Upload lease PDF → AI auto-fills fields]               │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│             CONNECT PAYMENTS                              │
│  ┌─────────┐  ┌──────┐  ┌───────┐                       │
│  │ Stripe  │  │ ACH  │  │ Zelle │                       │
│  └─────────┘  └──────┘  └───────┘                       │
│  Set up Stripe Connect for payouts                       │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│           ADD CONTRACTORS (Optional)                      │
│  Name │ Trade │ Phone │ Email │ Rate                     │
│  [Skip → use RealDeal contractor network]                │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              DASHBOARD READY                             │
│  "Your AI property manager is set up!"                   │
│  [View Dashboard]  [Invite Tenants]                      │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tenant Portal Flow

```
Tenant receives invite SMS/Email
         │
         ▼
┌─────────────────────────────┐
│   CREATE ACCOUNT            │
│   Phone verification (OTP)  │
└──────────┬──────────────────┘
           ▼
┌──────────────────────────────────────────┐
│           TENANT HOME                     │
│                                           │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Pay Rent │  │ Request  │  │  Docs  │ │
│  │          │  │ Repair   │  │        │ │
│  └──────────┘  └──────────┘  └────────┘ │
│                                           │
│  ┌──────────────────────────────────────┐ │
│  │    Chat with AI Assistant            │ │
│  │    "How can I help you today?"       │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  Payment History  │  Maintenance Status   │
└──────────────────────────────────────────┘
```

---

## 3. Maintenance Request Flow (Tenant Side)

```
Tenant taps "Request Repair"
         │
         ▼
┌──────────────────────────────────┐
│  DESCRIBE THE ISSUE              │
│  [Text description]              │
│  [Take/Upload Photo] (optional)  │
│  [Record voice note] (optional)  │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  AI PROCESSES                    │
│  "I see water damage on your     │
│   bathroom ceiling. I'm          │
│   classifying this as urgent     │
│   plumbing. Is that right?"      │
│                                  │
│  [Yes, correct]  [No, edit]      │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  CONFIRMATION                    │
│  "Got it! I'm contacting a       │
│   plumber now. You'll hear back  │
│   within 2 hours with timing."   │
│                                  │
│  Ticket #: MT-2024-0392          │
│  Status: Contractor Contacted    │
└──────────────────────────────────┘
```

---

## 4. Maintenance Request Flow (Landlord Side)

```
┌──────────────────────────────────────────────────────────┐
│  MAINTENANCE QUEUE                                        │
│                                                           │
│  🔴 EMERGENCY (0)    🟡 URGENT (2)    🟢 ROUTINE (5)     │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MT-0392 │ Unit 4B │ Plumbing │ Urgent               │ │
│  │ "Ceiling leak in bathroom"                           │ │
│  │ AI Diagnosis: Water damage, severity 3/5             │ │
│  │ Photo: [thumbnail]                                   │ │
│  │                                                      │ │
│  │ Quotes received:                                     │ │
│  │   ABC Plumbing:  $350  │ Available tomorrow 9am      │ │
│  │   QuickFix:      $420  │ Available today 4pm         │ │
│  │                                                      │ │
│  │ [Approve ABC] [Approve QuickFix] [Get more quotes]   │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Landlord Dashboard (Main Screen)

```
┌──────────────────────────────────────────────────────────────────┐
│  RealDeal AI                          [Notifications 🔔3]  [⚙️] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PORTFOLIO SNAPSHOT                     March 2026               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Units: 24  │ │Occupied:22 │ │ Collected  │ │  Outstanding │ │
│  │            │ │  (91.7%)   │ │  $38,400   │ │   $3,200     │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ NOI (Mo)   │ │ Cash Flow  │ │ Cap Rate   │ │ Maint Spend  │ │
│  │  $28,100   │ │  $14,200   │ │   6.8%     │ │   $4,300     │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  AI ACTIVITY FEED                                           │ │
│  │  10:42  Collected $1,800 from Tenant J. Smith (Unit 3A)     │ │
│  │  10:15  Scheduled plumber for Unit 4B (tomorrow 9am)        │ │
│  │  09:30  Answered lease question from Tenant M. Garcia       │ │
│  │  09:12  Sent rent reminder to 3 tenants                     │ │
│  │  08:45  ⚠️ Escalation: Tenant complaint needs your review   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Properties   │  │ Maintenance  │  │ Financials           │  │
│  │ [View All]   │  │ [View Queue] │  │ [View Reports]       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Navigation Structure

```
Landlord App
├── Dashboard (home)
├── Properties
│   ├── Property Detail
│   │   ├── Units List
│   │   ├── Unit Detail → Tenant Info
│   │   └── Property Financials
│   └── Add Property
├── Tenants
│   ├── Tenant List
│   ├── Tenant Detail (payments, requests, lease)
│   └── Invite Tenant
├── Maintenance
│   ├── Active Requests (kanban: New → Quoted → Scheduled → Complete)
│   ├── Request Detail
│   └── Contractor Directory
├── Finances
│   ├── Income Overview
│   ├── Expense Tracking
│   ├── P&L Reports
│   └── Tax Export
├── Documents
│   ├── All Documents (filterable)
│   ├── Upload
│   └── Lease Analyzer
├── Messages
│   ├── AI Conversation Log
│   ├── Escalated Items
│   └── Broadcast to Tenants
└── Settings
    ├── Account & Billing
    ├── Payment Setup
    ├── AI Preferences (auto-approve thresholds, escalation rules)
    ├── Notification Preferences
    └── Team Members
```
