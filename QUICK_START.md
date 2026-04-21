# Quick Start Guide - AI Sales Predictive Management

## 🚀 Get Running in 5 Minutes

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Start Development Server
```bash
npm run dev
```

### Step 3: Open in Browser
Visit `http://localhost:3000`

### Step 4: Login
Use any email/password (mock authentication):
- Email: `demo@example.com`
- Password: `password`

## 📊 What You'll See

### Pipeline Page (Default)
- 5-stage sales pipeline (Prospecting → Closed Won)
- 25+ deals with drag-and-drop management
- Win probability badges with color coding
- Deal values and stage metrics

### Deals Page
- Complete deal list with all information
- Create new deals with form
- Links to individual deal details
- Account and contact information

### Deal Detail Page
- Win probability trend chart
- Confidence interval visualization
- Top 5 signal factors
- Recent signal history
- Deal metrics and information

### Forecasts Page
- Revenue forecasts for 12 months
- Weekly/Monthly/Quarterly views
- Forecast vs Actual comparison
- Confidence bands visualization
- Export functionality

### Insights Page
- AI-generated actionable insights
- Sorted by revenue impact
- Act Upon and Dismiss buttons
- Color-coded insight types
- Links to related deals

### Billing Page
- Current subscription tier
- Usage metrics with progress bars
- Three tier options (Starter/Growth/Enterprise)
- Upgrade/Downgrade functionality
- Feature comparison

## 🎨 Features Demonstrated

### Data Visualization
- ✅ Line charts for trends
- ✅ Area charts for forecasts
- ✅ Composed charts for comparisons
- ✅ Progress bars for usage
- ✅ Color-coded status indicators

### Interactions
- ✅ Drag-and-drop pipeline
- ✅ Form creation and validation
- ✅ Modal confirmations
- ✅ Optimistic updates
- ✅ Loading states

### Design
- ✅ Professional Tailwind CSS styling
- ✅ Responsive layout
- ✅ Smooth animations
- ✅ Hover effects
- ✅ Accessibility features

## 📁 Project Structure

```
frontend/
├── src/
│   ├── pages/           # All page components
│   ├── components/      # Reusable components
│   ├── services/        # API and data services
│   ├── store/           # State management
│   └── App.tsx          # Main app
├── vite.config.ts       # Build config
├── tailwind.config.js   # Styling config
└── package.json         # Dependencies
```

## 🔧 Available Commands

```bash
# Development
npm run dev              # Start dev server

# Production
npm run build            # Build for production
npm run preview          # Preview production build

# Testing
npm run test             # Run tests
npm run test:watch      # Run tests in watch mode

# Linting
npm run lint            # Run ESLint
```

## 🌐 API Integration

### Current Mode: Mock Data
The app uses generated mock data - no backend required!

### To Connect Real Backend:
1. Update `API_BASE_URL` in `frontend/src/services/api.ts`
2. Set `mockMode = false`
3. Backend must implement the REST endpoints

## 🔐 Authentication

Currently uses mock authentication. To integrate Cognito:
1. Update `frontend/src/store/authStore.ts`
2. Add Cognito SDK
3. Configure environment variables

## 📊 Mock Data Included

- **25 Deals** - Various stages and win probabilities
- **12 Forecasts** - Monthly revenue projections
- **15 Insights** - Actionable recommendations
- **Billing Info** - Usage metrics and tier limits
- **Signals** - Engagement history per deal
- **Predictions** - Win probability trends

## 🎯 Key Pages

| Page | URL | Features |
|------|-----|----------|
| Pipeline | `/pipeline` | Kanban board, drag-and-drop |
| Deals | `/deals` | List, create, view details |
| Deal Detail | `/deals/:id` | Charts, signals, trends |
| Forecasts | `/forecasts` | Revenue projections, comparisons |
| Insights | `/insights` | AI recommendations, actions |
| Billing | `/billing` | Subscription, usage, tiers |

## 💡 Tips

1. **Drag deals** between pipeline stages
2. **Click deal names** to see detailed view
3. **Create new deals** using the form
4. **Act on insights** to provide feedback
5. **Change billing tier** to see usage limits update
6. **View charts** for trend analysis

## 🐛 Troubleshooting

### Port 3000 in use?
```bash
npm run dev -- --port 3001
```

### Module errors?
```bash
rm -rf node_modules package-lock.json
npm install
```

### Styles not loading?
```bash
npm run build
```

## 📚 Learn More

- [React Documentation](https://react.dev)
- [Recharts Documentation](https://recharts.org)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [React Query Documentation](https://tanstack.com/query)

## 🚀 Next Steps

1. Explore all pages and features
2. Try creating and managing deals
3. Review the mock data structure
4. Plan backend integration
5. Add real authentication
6. Connect to real API

## 📞 Support

For issues:
1. Check browser console for errors
2. Verify Node.js version (18+)
3. Clear node_modules and reinstall
4. Check environment variables

---

**Happy exploring! 🎉**

The application is fully functional with realistic data demonstrating all features of the AI Sales Predictive Management platform.
