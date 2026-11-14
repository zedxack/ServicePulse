# ServicePulse — Design System Specification

**Author:** Muhammadyusuf Usmonov  
**System Identity:** ServicePulse Enterprise Hybrid RMM & ITSM Platform  
**Purpose:** Technical Operations Command Center & Enterprise Self-Service Design System  
**Version:** 1.0.0 (Production Design System)  
**Status:** Canonical Design Reference  

---

## 1. Brand Identity & Design Philosophy

ServicePulse is an enterprise hybrid Remote Monitoring and Management (RMM) and IT Service Management (ITSM) platform. The design communicates:

- **Technical Excellence & Precision:** Clear information density, monospaced telemetry values, unambiguous status indicators.
- **Operational Intelligence:** High-contrast situational awareness where healthy states fade into a calm background while critical outages and warnings demand immediate visual attention.
- **Enterprise Maturity & Reliability:** Crisp graphite, slate, and navy foundations with electric cyan and signal blue accents rather than distracting playful gradients or glassmorphism.
- **Pulse / Signal Aesthetic:** Heartbeat telemetry badges, micro-accent gradient bars, real-time WebSocket connection pulses, and high-frequency operational telemetry.

---

## 2. Color System & Design Tokens

### 2.1 Canvas & Surface Tokens

| Token | Light Mode Value | Dark Mode (Command Center) | Purpose |
| :--- | :--- | :--- | :--- |
| `--sp-bg-canvas` | `#f8fafc` (Slate 50) | `#090d16` (Deep Obsidian) | App viewport background |
| `--sp-bg-surface` | `#ffffff` (White) | `#0f172a` (Slate 900) | Primary cards, tables, sidebar |
| `--sp-bg-surface-elevated` | `#ffffff` (White) | `#1e293b` (Slate 800) | Modals, drawers, dropdowns |
| `--sp-bg-surface-subtle` | `#f1f5f9` (Slate 100) | `#162032` (Deep Navy) | Table headers, search inputs |
| `--sp-bg-surface-active` | `#e2e8f0` (Slate 200) | `#24344d` (Active Slate) | Active items, hover states |

### 2.2 Border Tokens

| Token | Light Mode | Dark Mode | Usage |
| :--- | :--- | :--- | :--- |
| `--sp-border-subtle` | `#e2e8f0` | `rgba(255, 255, 255, 0.07)` | Card borders, table dividers |
| `--sp-border-default` | `#cbd5e1` | `rgba(255, 255, 255, 0.12)` | Input borders, elevated cards |
| `--sp-border-strong` | `#94a3b8` | `rgba(255, 255, 255, 0.22)` | Modals, active borders |
| `--sp-border-focus` | `#0284c7` | `#38bdf8` | Keyboard focus ring |

### 2.3 Semantic Telemetry & Status Palette (WCAG 2.2 AA Compliant)

| Semantic State | Foreground (Light) | Background (Light) | Foreground (Dark) | Background (Dark) |
| :--- | :--- | :--- | :--- | :--- |
| **Online / Healthy** | `#065f46` (Emerald 800) | `#ecfdf5` | `#34d399` (Emerald 400) | `rgba(16, 185, 129, 0.12)` |
| **Warning / Degraded** | `#92400e` (Amber 800) | `#fffbeb` | `#fbbf24` (Amber 400) | `rgba(245, 158, 11, 0.12)` |
| **Critical / Outage** | `#991b1b` (Red 800) | `#fef2f2` | `#f87171` (Red 400) | `rgba(239, 68, 68, 0.14)` |
| **Info / Telemetry** | `#1e40af` (Blue 800) | `#eff6ff` | `#7dd3fc` (Sky 300) | `rgba(56, 189, 248, 0.12)` |

---

## 3. Typography Hierarchy

ServicePulse pairs a modern sans-serif for UI labels and titles with a monospaced font for telemetry, IP addresses, dates, and device identifiers:

- **Primary UI Sans:** `Inter, system-ui, -apple-system, sans-serif`
- **Technical Monospace:** `'JetBrains Mono', 'Fira Code', ui-monospace, monospace`

### Scale & Weight Definitions

| Element | Size | Weight | Line Height | Font Family |
| :--- | :--- | :--- | :--- | :--- |
| **Page Title** | `24px` (`1.5rem`) | Bold (`700`) | `1.25` | Sans-Serif |
| **Section Heading** | `18px` (`1.125rem`) | SemiBold (`600`) | `1.3` | Sans-Serif |
| **Card / Modal Title** | `14px` (`0.875rem`) | SemiBold (`600`) | `1.4` | Sans-Serif |
| **Body Primary** | `13px` (`0.8125rem`)| Regular / Medium | `1.5` | Sans-Serif |
| **Table Header** | `11px` (`0.6875rem`)| Bold (`700`) | `1.2` (Uppercase) | Sans-Serif |
| **Telemetry / Metric** | `24px`–`32px` | Bold (`700`) | `1.1` | Monospace |
| **IP / Host / Code** | `11px`–`12px` | Medium (`500`) | `1.4` | Monospace |

---

## 4. Spacing, Elevation & Layout Grid

- **8pt Fluid Grid:** Standard spacings of `4px` (`0.25rem`), `8px` (`0.5rem`), `12px` (`0.75rem`), `16px` (`1rem`), `24px` (`1.5rem`), `32px` (`2rem`).
- **Layout Container:** Max width `1440px` centered with fluid gutters (`16px` mobile, `24px` tablet, `32px` desktop).
- **Elevation Layers:**
  1. Base Canvas (`0dp`)
  2. Surface Cards (`1dp` + `--sp-shadow-xs`)
  3. Interactive / Hover Cards (`2dp` + `--sp-shadow-sm`)
  4. Flyout Popovers & Command Palette (`4dp` + `--sp-shadow-md`)
  5. Modal Dialogs & Critical Drawers (`8dp` + `--sp-shadow-modal`)

---

## 5. Reusable Component Catalog

1. **`PulseIndicator`:** Heartbeat indicator with ping animation for live WebSocket state and host status.
2. **`Badge`:** Multi-variant technical badges (`online`, `offline`, `warning`, `info`, `purple`, `mono`).
3. **`MetricCard`:** Unified KPI card with micro-accent bar, delta trend, icon slot, and monospace value.
4. **`CommandPalette` (`Ctrl/Cmd + K`):** Global operational command bar enabling instant page jumping, actions, and language/theme switching.
5. **`ThemeToggle`:** Seamless dark, light, and system theme switcher.
6. **`Button`:** Standardized touch/click targets with loading spinner and accessibility focus rings.
7. **`LoadingSkeleton`:** Content-aware pulsing placeholder loading skeletons.
8. **`EmptyState`:** Consistent empty states with technical icons, explanations, and action triggers.

---

## 6. Accessibility & Motion Rules (WCAG 2.2 AA)

- **Color Contrast:** All body text meets at least 4.5:1 contrast against adjacent background. All headers and large metrics meet at least 3:1.
- **Focus Rings:** Distinct 2px focus ring (`--sp-border-focus`) on all interactive buttons, inputs, and links.
- **Reduced Motion:** Fully integrated `@media (prefers-reduced-motion: reduce)` disabling non-essential transitions and pulsing animations for users with vestibular sensitivities.
- **Keyboard Navigation:** Full tab order, Escape dismiss on modals, Arrow keys navigation in Command Palette.
