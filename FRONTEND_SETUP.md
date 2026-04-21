# AI Sales Predictive Management - Frontend Setup Guide

## Overview

The frontend is a modern React 18 application with TypeScript, featuring real-time data visualization, drag-and-drop pipeline management, and comprehensive billing/insights dashboards.

## Features Implemented

### ✅ Core Pages
- **Pipeline Kanban** - Drag-and-drop deal management with win probability visualization
- **Deal List** - Comprehensive deal table with creation form
- **Deal Detail** - Individual deal view with prediction trends and signal history
- **Forecasts** - Revenue forecasts with trend analysis and comparisons
- **Insights** - AI-generated actionable insights with act/dismiss functionality
- **Billing** - Subscription management with usage metrics and tier selection

### ✅ Data & Services
- **Mock Data Service** - 25+ realistic deals with signals and predictions
- **API Client** - Axios-based client with mock mode for development
- **React Query** - Server state management with caching
- **Zustand** - UI state management for auth and preferences

### ✅ UI/UX
- **Responsive Design** - Works on desktop and tablet
- **Tailwind CSS** - Modern styling with dark mode ready
- **Recharts** - Interactive charts for predictions and forecasts
- **Drag-and-Drop** - Kanban board with optimistic updates
- **Loading States** - Proper loading indicators and error handling

## Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

Output will be in `frontend/dist/`

## Project Structure

```
frontend/
├── src/
│   ├── pages/              # Page components
│   │   ├── DealListPage.tsx
│   │   ├── DealDetailPage.tsx
│   │   ├── PipelinePage.tsx
│   │   ├── ForecastPage.tsx
│   │   ├── InsightsPage.tsx
│   │   ├── BillingPage.tsx
│   │   └── LoginPage.tsx
│   ├── components/         # Reusable components
│   │   └── Layout.tsx
│   ├── services/           # API and data services
│   │   ├── api.ts          # API client
│   │   └── mockData.ts     # Mock data generator
│   ├── store/              # Zustand stores
│   │   └── authStore.ts
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
└── package.json
```

## Key Technologies

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router v6** - Routing
- **React Query** - Server state management
- **Zustand** - Client state management
- **Recharts** - Data visualization
- **Tailwind CSS** - Styling
- **Axios** - HTTP client

## API Integration

### Mock Mode (Development)

By default, the app runs in mock mode using generated data. No backend required.

```typescript
// frontend/src/services/api.ts
const apiClient = new ApiClient()
apiClient.setMockMode(true) // Enabled by default
```

### Real Backend Mode

To connect to a real backend:

1. Update `API_BASE_URL` in `frontend/src/services/api.ts`:
```typescript
const API_BASE_URL = 'https://your-api.com/api'
```

2. Disable mock mode:
```typescript
apiClient.setMockMode(false)
```

3. Ensure backend implements the following endpoints:
   - `GET /v1/deals`
   - `POST /v1/deals`
   - `GET /v1/deals/:id`
   - `PUT /v1/deals/:id`
   - `DELETE /v1/deals/:id`
   - `GET /v1/pipeline`
   - `GET /v1/pipeline/funnel`
   - `GET /v1/pipeline/heatmap`
   - `GET /v1/deals/:id/predictions`
   - `GET /v1/forecasts`
   - `GET /v1/forecasts/:id`
   - `GET /v1/insights`
   - `PUT /v1/insights/:id/act`
   - `PUT /v1/insights/:id/dismiss`
   - `GET /v1/billing`
   - `PUT /v1/billing/tier`

## Authentication

Currently uses mock authentication. To integrate with Cognito:

1. Update `frontend/src/store/authStore.ts`:
```typescript
// Replace mock login with Cognito
import { CognitoIdentityServiceProvider } from 'aws-sdk'
```

2. Configure Cognito credentials in environment variables

## Environment Variables

Create `.env` file in `frontend/`:

```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_COGNITO_DOMAIN=your-domain.auth.region.amazoncognito.com
REACT_APP_COGNITO_CLIENT_ID=your-client-id
REACT_APP_COGNITO_REDIRECT_URI=http://localhost:3000/callback
```

## Testing

```bash
# Run tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run linter
npm run lint
```

## Performance Optimizations

- Code splitting via Vite
- React Query caching with stale-while-revalidate
- Lazy loading of routes
- Optimistic updates for mutations
- Memoization of expensive computations

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Troubleshooting

### Port 3000 already in use
```bash
npm run dev -- --port 3001
```

### Module not found errors
```bash
rm -rf node_modules package-lock.json
npm install
```

### Tailwind styles not loading
```bash
npm run build
```

## Next Steps

1. **Connect to Backend** - Update API client to point to real backend
2. **Add Authentication** - Integrate with Cognito
3. **WebSocket Support** - Add real-time updates
4. **Dark Mode** - Implement theme toggle
5. **Mobile Optimization** - Improve mobile UX
6. **Analytics** - Add usage tracking
7. **Error Tracking** - Integrate Sentry or similar

## Support

For issues or questions, check:
- React documentation: https://react.dev
- Recharts documentation: https://recharts.org
- Tailwind CSS documentation: https://tailwindcss.com
- React Query documentation: https://tanstack.com/query
