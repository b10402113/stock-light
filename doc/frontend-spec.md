## Framework

React + Vite + Tailwind CSS v4

## Project Overview

This is a React **mobile web application** for StockLight - a stock price notification service. Users can subscribe to stock price or technical indicator triggers via LINE, and the system automatically monitors and pushes notifications.

The frontend is designed as a **mobile-first** single-page application (SPA) with a clean, minimalist interface optimized for smartphone viewing.

## Navigation Bar

**Bottom navigation bar** (fixed position, from left to right):

| Icon | Label | Route | Description |
|------|-------|-------|-------------|
| 🏠 | Home | `/home` | Dashboard with subscription overview and history |
| 🔍 | Search | `/search` | Search stocks by symbol or name |
| ➕ | Add | `/add` | Create new subscription notification |
| 📊 | Backtest | `/backtest` | Investment strategy simulation |
| 👤 | Profile | `/profile` | User settings and membership |

**Navigation styling**:
- Deep brown background (#4A3728) in light mode, darker brown (#2D1F14) in dark mode
- Active tab highlighted with cream accent (#F5E6D3)
- Icons use inline SVG for crisp rendering
- Safe area padding for iOS devices (env(safe-area-inset-bottom))

## Pages Layout

### Home

**Statistics Cards (Top Row)**:
- Two equal-width cards with rounded corners (radius: 12px)
- Left card: **Active Subscriptions** count with stock icon
- Right card: **Today's Alerts** triggered count with bell icon
- Deep brown border (1px) with cream background in light mode

**Subscription List (Main Section)**:
- Card-based list showing user's subscribed stocks
- Each card contains:
  - Stock symbol and name (e.g., "2330 台積電")
  - Current price with change percentage (green/red)
  - Subscription type badge (技術指標 / 定期提醒)
  - Settings button (gear icon) → opens edit modal
- Keyset pagination (cursor-based) with infinite scroll
- Empty state message when no subscriptions

**Backtest History (Bottom Section)**:
- Collapsible section showing recent backtest records
- List items show: stock symbol, date range, strategy type, result summary
- Click to view detailed backtest results

### Search

**Search Bar**:
- Full-width search input at top
- Placeholder: "Search by symbol or name..."
- Auto-clear button (X icon)
- Deep brown focus border

**Search Results**:
- Real-time filtering as user types
- Each result shows:
  - Stock symbol (bold, larger font)
  - Company name (secondary text)
  - Current price (right-aligned)
  - Quick-add button (+ icon) → redirects to Add page with pre-filled stock

**Empty States**:
- Initial: "Start typing to search stocks"
- No results: "No stocks found matching your query"

### Add Subscription

**Stock Selection Header**:
- Displays selected stock info (passed from Search or selected manually)
- Editable stock symbol input with autocomplete

**Subscription Type Tabs**:
- Two tabs with pill-shaped styling:
  1. **Condition Alert** (技術指標通知)
  2. **Scheduled Reminder** (定期提醒)

---

#### Tab 1: Condition Alert

**Alert Configuration Form**:
- **Alert Title**: Text input (max 50 chars)
- **Alert Message**: Textarea (max 200 chars)
- **Signal Type**: Radio buttons (Buy / Sell)

**Condition Builder**:
- Add condition button (+ Add Condition)
- Each condition row:
  - Indicator dropdown (RSI, MACD, KD, Price, Moving Average)
  - Operator dropdown (<, >, =, crosses above, crosses below)
  - Value input (numeric)
- Logical operator: AND (Premium users can add multiple conditions, free users limited to 1)

**Examples**:
- "2330, RSI < 30 → Notify"
- "0050, Price < 200-day MA → Notify"
- "0050, Price < 200-day MA AND RSI < 50 → Notify"

**Preview Section**:
- Shows human-readable condition summary
- Example preview: "Notify me when 2330 台積電 RSI falls below 30"

---

#### Tab 2: Scheduled Reminder

**Reminder Configuration Form**:
- **Reminder Title**: Text input
- **Reminder Message**: Textarea

**Frequency Settings**:
- Frequency type: Daily / Weekly / Monthly
- Time picker: Select notification time (e.g., 17:00)

**Weekly/Monthly Options**:
- Weekly: Day selector (Mon-Sun checkboxes)
- Monthly: Day of month input (1-28)
- Example: "Every Wednesday at 17:00"
- Example: "Every 15th of the month"

**Examples**:
- "0050 - Every Wednesday 17:00"
- "00631L - Monthly on 15th"

**Submit Button**:
- Deep brown button with cream text
- Loading spinner on submission
- Success toast notification

### Backtest

**Backtest Parameters Form**:

| Parameter | Input Type | Description |
|-----------|-----------|-------------|
| Stock Symbol | Search input | Select stock to backtest |
| Date Range | Date picker | From/To dates (e.g., 2020-05-10 to 2026-05-10) |
| Investment Type | Radio group | Single investment / Periodic investment |
| Periodic Frequency | Dropdown | Monthly / Weekly (if periodic selected) |
| Investment Amount | Number input | Amount per period or single amount |

**Condition Builder** (for strategy-based backtesting):
- **Buy Conditions**: Add indicator-based buy rules
- **Sell Conditions**: Add indicator-based sell rules
- Free users: Maximum 1 condition per buy/sell
- Premium users: Multiple conditions with AND logic

**Condition Examples**:
- Buy: "RSI < 30 AND Price < 200-day MA"
- Sell: "RSI > 70 AND Price > 20-day MA"

**Calculate Button**:
- Deep brown button, cream text
- Loading animation during calculation
- Results displayed below after completion

**Results Display**:
- Summary cards: Total return, Annualized return, Max drawdown
- Chart: Portfolio value over time (line chart using Chart.js or Recharts)
- Transaction history table: Buy/sell dates, prices, amounts

### Profile

**User Information Card**:
- Avatar placeholder (circle with user initials)
- Username display (editable)
- Email display (read-only)
- Account creation date

**Membership Section**:
- Current plan badge (Free / Premium)
- Premium upgrade button (deep brown, cream text)
- Benefits list:
  - Free: 3 subscriptions, 1 backtest condition
  - Premium: Unlimited subscriptions, multiple conditions, advanced indicators

**Settings Section**:
- **Theme Toggle**: Light / Dark mode switch
- **Notification Preferences**: LINE notification toggle
- **Language**: English / Chinese (future feature)
- **Delete Account**: Danger button (red), confirmation modal

**Subscription Management**:
- Quick overview of active subscriptions count
- Link to manage all subscriptions

## UI/UX Design System

### Color Palette

**Light Mode (Primary)**:
| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| Background | Cream | #F5E6D3 | Page background, cards |
| Primary | Deep Brown | #4A3728 | Buttons, navigation, headers |
| Secondary | Warm Brown | #6B4E3D | Borders, secondary text |
| Accent | Mocha | #8B5A3C | Hover states, highlights |
| Text | Dark Brown | #2D1F14 | Primary text |
| Text Secondary | Medium Brown | #5A4030 | Secondary text |
| Success | Forest Green | #2E7D32 | Positive changes, buy signals |
| Error | Warm Red | #C62828 | Negative changes, sell signals |

**Dark Mode**:
| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| Background | Dark Brown | #1A1410 | Page background |
| Surface | Darker Brown | #2D1F14 | Cards, elevated surfaces |
| Primary | Warm Brown | #6B4E3D | Buttons, navigation |
| Accent | Cream | #F5E6D3 | Active states, highlights |
| Text | Cream | #F5E6D3 | Primary text |
| Text Secondary | Light Brown | #C4A88C | Secondary text |

### Typography

- **Font Family**: Inter (system fallback: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)
- **Heading Sizes**:
  - H1: 24px, font-weight 700 (page titles)
  - H2: 20px, font-weight 600 (section titles)
  - H3: 16px, font-weight 600 (card titles)
- **Body Text**: 14px, font-weight 400
- **Small Text**: 12px, font-weight 400 (labels, timestamps)

### Component Styling

**Buttons**:
- Primary: Deep brown background, cream text, rounded corners (8px)
- Hover: Mocha accent, slight shadow
- Active: Pressed state with darker shade
- Disabled: 50% opacity, no hover effect

**Cards**:
- Background: Cream (light) / Dark brown (dark)
- Border: 1px solid warm brown
- Border radius: 12px
- Padding: 16px
- Shadow: Subtle drop shadow (0 2px 4px rgba(0,0,0,0.1))

**Input Fields**:
- Background: White (light) / Darker brown (dark)
- Border: 1px warm brown, rounded corners (6px)
- Focus: Deep brown border (2px), cream glow
- Placeholder: Medium brown text (light mode)

**Tags/Badges**:
- Pill-shaped (rounded-full)
- Background: Mocha accent
- Text: Cream
- Font size: 12px

### Design Principles

- **Minimalist**: Clean layouts, no unnecessary decorations
- **Reading-focused**: High legibility, generous whitespace (24px gaps)
- **Mobile-first**: Touch-friendly targets (min 44px height), swipe gestures
- **Consistent**: Reusable component patterns across all pages
- **Accessible**: WCAG 2.1 AA compliance, proper contrast ratios

### Animation & Transitions

- Theme toggle: Smooth transition (300ms ease)
- Modal open/close: Fade + slide up (200ms)
- List item hover: Subtle scale (1.02) + shadow
- Button click: Quick press animation (100ms)

### Reference Designs

- Medium (clean typography, generous whitespace)
- Substack (mobile-friendly newsletter layout)
- Notion Light Mode (minimalist card design)
- Modern knowledge blogs (reading-focused UX)

## Theme Switching Implementation

### Theme Provider

Use React Context for global theme state:

```tsx
// ThemeContext.tsx
type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

// Persist theme preference in localStorage
// Default to light mode
// Respect system preference on first visit
```

### Tailwind Configuration

```js
// tailwind.config.js
module.exports = {
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        brown: {
          50: '#F5E6D3',
          100: '#E8D4BE',
          200: '#C4A88C',
          300: '#A07F5A',
          400: '#8B5A3C',
          500: '#6B4E3D',
          600: '#4A3728',
          700: '#2D1F14',
          800: '#1A1410',
          900: '#0D0906',
        }
      }
    }
  }
}
```

### CSS Variables (Alternative)

```css
:root {
  --bg-primary: #F5E6D3;
  --bg-surface: #FFFFFF;
  --text-primary: #2D1F14;
  --accent: #4A3728;
}

.dark {
  --bg-primary: #1A1410;
  --bg-surface: #2D1F14;
  --text-primary: #F5E6D3;
  --accent: #6B4E3D;
}
```

### Theme Toggle Component

```tsx
// ThemeToggle.tsx
<button onClick={toggleTheme} className="...">
  {theme === 'light' ? (
    <MoonIcon /> // Switch to dark
  ) : (
    <SunIcon />  // Switch to light
  )}
</button>
```

Store preference in localStorage for persistence across sessions.

## Mobile Considerations

- **Viewport**: meta viewport tag with proper scaling
- **Touch targets**: Minimum 44px height/width for buttons
- **Swipe gestures**: Pull-to-refresh (optional), swipe navigation (optional)
- **iOS safe areas**: env(safe-area-inset-bottom) for bottom nav
- **Performance**: Lazy load images, code splitting per route
- **PWA features**: Service worker, offline support (optional)
- **Haptic feedback**: Consider for button presses (iOS)

## Responsive Breakpoints

Since this is mobile-only:
- **Default**: 375px - 428px (iPhone SE to iPhone 14 Pro Max)
- **Small**: < 375px (older iPhones)
- **Large**: > 428px (larger phones, tablets)
- Bottom navigation always visible, never hidden

## Accessibility

- Color contrast ratios meet WCAG 2.1 AA (minimum 4.5:1)
- Focus states visible for keyboard navigation
- Screen reader friendly labels (aria-label)
- Semantic HTML structure
- Touch gestures have alternative button controls