# macOS Dark Mode UI Redesign — Design Spec

**Goal:** Restyle the entire frontend from the current terminal/hacker aesthetic to a macOS Dark Mode look — warm grays, Apple system colors, SF Pro typography, rounded corners, subtle depth. Pure styling pass — zero backend or functionality changes.

---

## Design System

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#1c1c1e` | Page background, sidebar |
| `--bg-secondary` | `#2c2c2e` | Cards, surfaces |
| `--bg-elevated` | `#3a3a3c` | Elevated elements, hover states |
| `--text-primary` | `#e5e5e7` | Headings, body text |
| `--text-secondary` | `#98989d` | Metadata, captions |
| `--text-tertiary` | `#636366` | Section labels, disabled |
| `--accent` | `#0a84ff` | Active nav, links, selected states |
| `--accent-bg` | `rgba(10,132,255,0.15)` | Active nav background, accent badges |
| `--border` | `#3a3a3c` | Card borders, dividers |
| `--border-subtle` | `#2c2c2e` | Subtle separators |
| `--green` | `#30d158` | Bullish, success, healthy |
| `--red` | `#ff453a` | Bearish, error, unhealthy |
| `--orange` | `#ff9f0a` | Warning, caution |
| `--yellow` | `#ffd60a` | Economy topic |
| `--purple` | `#bf5af2` | Crypto topic |
| `--pink` | `#ff375f` | Prediction markets |
| `--teal` | `#64d2ff` | Real estate, fintech |

### Typography

```css
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif;
```

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Page title | 28px | 700 | `--text-primary` |
| Section heading | 20px | 600 | `--text-primary` |
| Card title | 15px | 500 | `--text-primary` |
| Body text | 14px | 400 | `--text-primary` |
| Metadata | 12px | 400 | `--text-secondary` |
| Section label | 11px | 600 | `--text-tertiary`, uppercase, letter-spacing 0.5px |
| Badge | 11px | 500 | Matching topic color |

### Borders & Radius

- Cards: `border-radius: 10px`, `border: 1px solid var(--border)`
- Badges/pills: `border-radius: 6px`
- Buttons: `border-radius: 8px`
- Input fields: `border-radius: 8px`
- All borders 1px (not 2px)

### Shadows

- Cards: `box-shadow: 0 1px 3px rgba(0,0,0,0.2)`
- Elevated (dropdowns, tooltips): `box-shadow: 0 4px 12px rgba(0,0,0,0.3)`
- No shadows on flat elements

### Spacing

- Card padding: 16px
- Card gap: 12px
- Section gap: 24px
- Sidebar item padding: 8px 12px
- Page padding: 24px

---

## Component Styling

### Sidebar (`sidebar-nav.tsx`)

- Width: 220px, fixed
- Background: `#1c1c1e`
- Border-right: `1px solid #3a3a3c`
- App title: 15px, 600 weight, `#e5e5e7`, with a small RSS icon
- Section label: 11px uppercase, `#636366`, `letter-spacing: 0.5px`
- Nav items: 13px, `#98989d` text, `border-radius: 6px`, `padding: 7px 12px`
- Active item: `#0a84ff` text, `rgba(10,132,255,0.15)` background
- Hover: `#e5e5e7` text, `rgba(255,255,255,0.05)` background
- Icons: 16px, same color as text

### Cards (headline cards, event cards, etc.)

- Background: `#2c2c2e`
- Border: `1px solid #3a3a3c`
- Border-radius: 10px
- Padding: 16px
- Box-shadow: `0 1px 3px rgba(0,0,0,0.2)`
- Title: 15px, 500 weight, `#e5e5e7`
- Metadata row: 12px, `#98989d`, items separated by ` · `
- Hover: border shifts to `#48484a`

### Topic Badges

Small pills with muted colored backgrounds:

| Topic | Background | Text |
|-------|-----------|------|
| markets | `rgba(48,209,88,0.15)` | `#30d158` |
| economy | `rgba(255,214,10,0.15)` | `#ffd60a` |
| earnings | `rgba(255,159,10,0.15)` | `#ff9f0a` |
| crypto | `rgba(191,90,242,0.15)` | `#bf5af2` |
| commodities | `rgba(255,69,58,0.15)` | `#ff453a` |
| real_estate | `rgba(100,210,255,0.15)` | `#64d2ff` |
| regulation | `rgba(10,132,255,0.15)` | `#0a84ff` |
| fintech | `rgba(48,209,88,0.15)` | `#30d158` |
| prediction_markets | `rgba(255,55,95,0.15)` | `#ff375f` |
| mergers | `rgba(191,90,242,0.15)` | `#bf5af2` |
| general | `rgba(152,152,157,0.15)` | `#98989d` |

Badge style: `border-radius: 6px`, `padding: 2px 8px`, `font-size: 11px`, `font-weight: 500`

### Sentiment Indicators

- Bullish: `#30d158` (Apple green) — small up-arrow or "Bullish" text
- Bearish: `#ff453a` (Apple red) — small down-arrow or "Bearish" text
- Neutral: `#98989d` — dash or "Neutral" text
- Sentiment bars: same colors, rounded ends

### Buttons

- Primary: `#0a84ff` background, white text, `border-radius: 8px`, no border
- Secondary: transparent, `1px solid #48484a`, `#e5e5e7` text, `border-radius: 8px`
- Hover: slightly lighter background
- Disabled: `#48484a` background, `#636366` text

### Inputs & Selects

- Background: `#1c1c1e`
- Border: `1px solid #48484a`
- Border-radius: 8px
- Text: `#e5e5e7`
- Focus: `border-color: #0a84ff`, `box-shadow: 0 0 0 3px rgba(10,132,255,0.25)`
- Placeholder: `#636366`

### Charts (Recharts)

- Chart area background: transparent (inherits card bg)
- Grid lines: `#3a3a3c`
- Axis text: 11px, `#636366`
- Tooltip: `#3a3a3c` background, `#e5e5e7` text, `border-radius: 8px`, `border: 1px solid #48484a`
- Bar colors: Apple system palette
- Heatmap cells: `#30d158` intensity scale (from `rgba(48,209,88,0.1)` to `rgba(48,209,88,0.9)`)

### Loading State

- Replace current spinner with a subtle pulsing dot or macOS-style indeterminate bar
- `#0a84ff` accent color
- Centered, minimal

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/app/globals.css` | Replace global styles: background, text colors, font family, remove monospace, add CSS custom properties |
| `frontend/src/app/layout.tsx` | Update font import (remove Space_Mono, use system font), update body classes |
| `frontend/src/components/sidebar-nav.tsx` | Restyle sidebar: warm grays, rounded active states, Apple blue accent |
| `frontend/src/components/data-sidebar.tsx` | Restyle right sidebar/stats panel |
| `frontend/src/components/loading.tsx` | Replace spinner with macOS-style loader |
| `frontend/src/app/page.tsx` | Restyle feed: card backgrounds, topic badges, sentiment icons, filters, search |
| `frontend/src/app/events/page.tsx` | Restyle event cards and event type badges |
| `frontend/src/app/analytics/page.tsx` | Restyle charts: colors, tooltips, grid lines, chart containers |
| `frontend/src/app/insights/page.tsx` | Restyle all sections: sentiment bars, cluster list, category volume |
| `frontend/src/app/predictions/page.tsx` | Restyle divergence cards, cross-reference cards |
| `frontend/src/app/pipeline/page.tsx` | Restyle action buttons, status card, log viewer, run history |
| `frontend/src/app/sources/page.tsx` | Restyle source list, health indicators, category badges |
| `frontend/src/app/settings/page.tsx` | Restyle all settings sections, toggles, dropdowns |

## What Does NOT Change

- All functionality, data flow, API calls
- Component structure, page routing
- Recharts library (just restyled)
- shadcn/ui base (just Tailwind overrides)
- Backend — zero changes
