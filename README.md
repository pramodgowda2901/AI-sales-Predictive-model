🤖 SalesPred AI — AI-Powered Sales Predictive Management SaaS
A full-stack B2B SaaS platform that uses machine learning to predict deal win probability, forecast revenue, and generate actionable sales insights in real time.

Home page with pricing, features, testimonials	Drag-and-drop pipeline with win probability	AI-ranked insights with act/dismiss
🚀 Live Demo
Frontend:  http://localhost:3000
Backend:   http://localhost:8000

Demo Login:
  Email:    demo@example.com
  Password: demo123

Test Payment Card: 4242 4242 4242 4242
✨ Features
Core Sales Features
AI Win Probability Scoring — Real-time ML scoring on every deal using Amazon SageMaker. Confidence intervals included.
Revenue Forecasting — Weekly, monthly, and quarterly forecasts with upper/lower confidence bands. CSV/JSON export.
Smart Insights — AI-generated recommendations ranked by revenue impact. Stalled deal alerts, next best actions.
Pipeline Kanban — Drag-and-drop pipeline management with real-time win probability on every card.
Deal Management — Full CRUD with advanced filters, bulk operations (stage change, delete, export), sortable columns.
Analytics & Reporting
Analytics Dashboard — Dynamic metrics by date range (Week/Month/Quarter/Year). Top performers leaderboard.
Report Builder — Pick metrics, group by dimension, choose chart type (Bar/Line/Pie/Table), save and schedule reports.
Forecast vs Actual — Side-by-side comparison charts with deviation detection.
Platform Features
Dark Mode — Full dark theme toggle that persists across sessions.
Global Search — Search across deals, forecasts, and insights with keyboard navigation (⌘K).
Real-time Updates — Live polling every 15 seconds + live activity feed on Pipeline.
Notification Center — Slide-over panel with badge counter, grouped by date, mark-as-read.
CRM Integrations — Connect Salesforce, HubSpot, Microsoft Dynamics with OAuth flow simulation.
Authentication & Security
Full Auth Flow — Signup, Login, Forgot Password, Reset Password with real-time password validation.
Payment Processing — Stripe-style payment modal with card validation and tier upgrades.
Role-Based Access — Admin, Manager, Sales Rep roles with permission enforcement.
GDPR/CCPA — Data export and deletion request endpoints.
API Keys — Create, revoke, and manage API keys with masked display.
Admin & Management
User Management — Invite users, edit roles, remove users, toggle active/inactive status.
Super Admin Dashboard — Platform-wide metrics, tenant management, health monitoring, revenue charts.
Onboarding Wizard — 4-step guided setup (CRM, Team, Pipeline, Sample Data).
Email Preferences — 6 email categories with toggle switches and unsubscribe all.
Settings — Profile, Notifications, Security (2FA, change password, sessions), Integrations.
🏗️ Tech Stack
Frontend
Technology	Purpose
React 18 + TypeScript	UI framework
Vite	Build tool
Tailwind CSS	Styling with dark mode
React Query	Server state management
Zustand	Client state (auth, UI)
Recharts	Charts (Bar, Line, Pie, Area)
React Router v6	Client-side routing
Axios	HTTP client
Backend
Technology	Purpose
Node.js + Express	REST API server
TypeScript	Type safety
crypto (built-in)	Password hashing, token generation
Infrastructure (AWS CDK)
Stack	Purpose
NetworkStack	VPC, subnets, security groups
DataStack	Aurora PostgreSQL, ElastiCache Redis, S3
AuthStack	Cognito user pools, RBAC, SSO
ApiStack	API Gateway (REST + WebSocket)
ComputeStack	ECS Fargate, ALB, WAF
MLStack	SageMaker endpoints, Model Registry
EmailStack	SES, SQS email queue
ObservabilityStack	CloudWatch dashboards, alarms
PipelineStack	CodePipeline CI/CD
ML Pipeline
Component	Purpose
train.py
XGBoost + LightGBM training
features.py
Feature engineering pipeline
evaluate.py
Model evaluation and reporting
📁 Project Structure
salespred-ai/
├── frontend/                  # React 18 SPA
│   ├── src/
│   │   ├── pages/             # 20 pages
│   │   │   ├── LandingPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── SignupPage.tsx
│   │   │   ├── PipelinePage.tsx
│   │   │   ├── DealListPage.tsx
│   │   │   ├── DealDetailPage.tsx
│   │   │   ├── ForecastPage.tsx
│   │   │   ├── InsightsPage.tsx
│   │   │   ├── AnalyticsPage.tsx
│   │   │   ├── BillingPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── AdminPage.tsx
│   │   │   ├── APIKeysPage.tsx
│   │   │   ├── OnboardingPage.tsx
│   │   │   ├── EmailPreferencesPage.tsx
│   │   │   ├── SuperAdminPage.tsx
│   │   │   ├── DataPrivacyPage.tsx
│   │   │   ├── CRMIntegrationPage.tsx
│   │   │   └── ReportsPage.tsx
│   │   ├── components/        # Shared components
│   │   │   ├── Layout.tsx
│   │   │   ├── BackButton.tsx
│   │   │   ├── NotificationCenter.tsx
│   │   │   ├── GlobalSearch.tsx
│   │   │   ├── WsStatus.tsx
│   │   │   ├── LiveFeed.tsx
│   │   │   └── PaymentModal.tsx
│   │   ├── services/
│   │   │   ├── api.ts         # 40+ API methods
│   │   │   └── mockData.ts    # Mock data generators
│   │   ├── store/
│   │   │   ├── authStore.ts   # Auth state (Zustand)
│   │   │   └── uiStore.ts     # Dark mode, WS status
│   │   └── hooks/
│   │       └── useRealTimeUpdates.ts
│   ├── server.cjs             # Express static server
│   └── package.json
├── backend/                   # Express API server
│   ├── mock-api.ts            # 30+ endpoints
│   ├── mock-data.ts           # Self-contained data
│   └── package.json
├── cdk/                       # AWS CDK infrastructure
│   ├── stacks/                # 9 CDK stacks
│   ├── lib/                   # Shared constructs
│   └── bin/                   # App entry point
├── ml/                        # Python ML scripts
│   ├── train.py
│   ├── features.py
│   └── evaluate.py
├── packages/                  # Microservices
│   ├── auth-service/
│   ├── deal-service/
│   ├── billing-service/
│   ├── chart-data-service/
│   └── shared/
└── .kiro/specs/               # Spec-driven development docs
    └── ai-sales-predictive-management/
        ├── requirements.md
        ├── design.md
        └── tasks.md
🛠️ Getting Started
Prerequisites
Node.js v18+
npm v9+
1. Clone the repository
git clone https://github.com/yourusername/salespred-ai.git
cd salespred-ai
2. Start the Backend
cd backend
npm install
npx tsc -p tsconfig.json
node dist/mock-api.js
# Backend running at http://localhost:8000
3. Start the Frontend
cd frontend
npm install
npm run build
node server.cjs
# Frontend running at http://localhost:3000
4. Open in browser
http://localhost:3000
You will land on the home page. Click Sign In and use the demo credentials:

Email:    demo@example.com
Password: demo123
🔑 Environment Variables
For production deployment, set these in your environment:

# Frontend
REACT_APP_API_URL=https://your-api-domain.com/api

# Backend
PORT=8000
NODE_ENV=production
JWT_SECRET=your-jwt-secret
STRIPE_SECRET_KEY=sk_live_...
AWS_REGION=us-east-1
📊 Pages Overview
Route	Page	Auth Required
/	Landing Page	No
/login	Sign In	No
/signup	Create Account	No
/forgot-password	Password Reset	No
/pipeline	Kanban Board	Yes
/deals	Deal List	Yes
/deals/:id	Deal Detail	Yes
/forecasts	Revenue Forecasts	Yes
/insights	AI Insights	Yes
/analytics	Analytics Dashboard	Yes
/billing	Billing & Payments	Yes
/settings	Account Settings	Yes
/admin	User Management	Yes (Admin)
/api-keys	API Keys	Yes
/onboarding	Setup Wizard	Yes
/email-preferences	Email Settings	Yes
/super-admin	Platform Dashboard	Yes (Admin)
/data-privacy	GDPR/CCPA	Yes
/crm-integrations	CRM Connections	Yes
/reports	Report Builder	Yes
🔐 Security Features
Password validation (8+ chars, uppercase, lowercase, number, special char)
JWT token-based authentication
Password reset with expiring tokens (1 hour)
Payment session expiration (15 minutes)
Role-based access control (Admin / Manager / Sales Rep)
GDPR data export and deletion endpoints
AES-256 encryption at rest (AWS KMS in production)
TLS 1.2+ in transit
SOC 2 Type II compliant architecture
💳 Subscription Tiers
Feature	Starter ($99/mo)	Growth ($299/mo)	Enterprise ($999/mo)
Users	5	25	Unlimited
Deals	100	1,000	Unlimited
API Requests	10K/mo	100K/mo	1M/mo
CRM Integrations	—	✓	✓
Custom ML Models	—	—	✓
SSO / SAML	—	✓	✓
SLA	99.9%	99.9%	99.95%
Support	Email	Priority	24/7 Phone
🤝 Contributing
Fork the repository
Create your feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
