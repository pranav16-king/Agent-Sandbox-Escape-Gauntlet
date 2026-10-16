---
name: agentgauntlet-design
description: Design system for the sandboxX security dashboard (React + TSX + Tailwind). Use when building or reviewing any sandboxX UI - covers the four themes (Light, Dark, Black, Grey), required color pairings, decision colors (allow/block/ask), tokens, layout sizing, and component rules. No blue or purple anywhere.
---

# sandboxX Design Skill

Apply these rules to every screen, component, chart and state in the dashboard. Use tokens only. Never hard-code hex values in components.

## 1. Hard rules

1. **No blue and no purple** anywhere (UI, charts, icons, focus rings, links).
2. **Neutral surfaces. Color only carries meaning.**
   - Allow = green, Block = red, Ask = orange.
   - Yellow is the brand and focus accent (Light and Dark themes).
3. **Never rely on color alone.** Every decision badge = color + icon + text label:
   - `✓ ALLOW`, `✕ BLOCK`, `? ASK`
4. **Tokens only.** Components use Tailwind token classes (`bg-surface`, `text-ink`, `border-line`, `text-allow`...). A raw hex in a component is a bug.
5. **Hostile text.** `agent_thought`, `user_input`, `args`, `reason` are attacker-influenced. Render as plain escaped text. Never use `dangerouslySetInnerHTML`.
6. **Code is TSX.** No plain JSX.
7. All four themes must work on every page, with no flash of the wrong theme on load.

## 2. Themes and required color combinations

| Token | Light | Dark | Black | Grey |
|---|---|---|---|---|
| `--bg` | #F6F5F1 | #121413 | #000000 | #D9DCDD |
| `--surface` | #FFFFFF | #1A1D1C | #0B0B0B | #ECEEEE |
| `--raised` | #F0EEE7 | #222625 | #161616 | #F6F7F7 |
| `--border` | #E4E1D8 | #2F3432 | #2A2A2A | #BFC3C5 |
| `--text` | #1C1B18 | #E8ECE9 | #F5F5F5 | #1F2325 |
| `--muted` | #6B675C | #9BA39E | #9A9A9A | #4F575B |
| `--accent` | #F2B705 | #E3B341 | #FFFFFF | #2F3437 |
| `--on-accent` | #1C1B18 | #14120A | #000000 | #FFFFFF |
| `--allow` | #1E7B3A | #4ADE80 | #4ADE80 | #1B6E37 |
| `--block` | #B42318 | #F87171 | #FF6B6B | #A4261B |
| `--ask` | #C2410C | #FB923C | #FFA94D | #A8470A |

Tint tokens `--allow-bg`, `--block-bg`, `--ask-bg` = the matching color at ~12% opacity over `--surface`, in every theme.

Theme character: **Light** warm paper with yellow accent. **Dark** charcoal. **Black** true black, maximum contrast, white accent. **Grey** soft, low glare, dark-grey accent.

### Required pairings (what may sit on what)

| Foreground | Allowed background | Use |
|---|---|---|
| `text` | `bg`, `surface`, `raised` | Body text |
| `muted` | `bg`, `surface`, `raised` | Secondary text, labels, timestamps |
| `on-accent` | `accent` | Primary button, active nav item, selected chip |
| `allow` | `allow-bg`, `surface` | Allow badge, allowed row tint |
| `block` | `block-bg`, `surface` | Block badge, blocked row tint |
| `ask` | `ask-bg`, `surface` | Ask badge, pending approval card |
| `accent` | `bg`, `surface` | Focus ring, brand mark (never body text in Light) |

Never place `allow`, `block` or `ask` text on each other's tinted backgrounds, and never put `muted` on `accent`.

### Contrast status
Ratios were **estimated, not measured**. Before release, run every pair above through a contrast checker in all four themes. Targets: 4.5:1 for text, 3:1 for icons and chart marks. Adjust tokens (not components) if a pair fails.

## 3. Implementation

`theme/tokens.css` stores colors as space-separated RGB channels so Tailwind alpha works:

```css
:root, [data-theme='light'] {
  color-scheme: light;
  --bg: 246 245 241;  --surface: 255 255 255;  --raised: 240 238 231;
  --border: 228 225 216;  --text: 28 27 24;  --muted: 107 103 92;
  --accent: 242 183 5;  --on-accent: 28 27 24;
  --allow: 30 123 58;  --block: 180 35 24;  --ask: 194 65 12;
}
[data-theme='dark'] {
  color-scheme: dark;
  --bg: 18 20 19;  --surface: 26 29 28;  --raised: 34 38 37;
  --border: 47 52 50;  --text: 232 236 233;  --muted: 155 163 158;
  --accent: 227 179 65;  --on-accent: 20 18 10;
  --allow: 74 222 128;  --block: 248 113 113;  --ask: 251 146 60;
}
[data-theme='black'] {
  color-scheme: dark;
  --bg: 0 0 0;  --surface: 11 11 11;  --raised: 22 22 22;
  --border: 42 42 42;  --text: 245 245 245;  --muted: 154 154 154;
  --accent: 255 255 255;  --on-accent: 0 0 0;
  --allow: 74 222 128;  --block: 255 107 107;  --ask: 255 169 77;
}
[data-theme='grey'] {
  color-scheme: light;
  --bg: 217 220 221;  --surface: 236 238 238;  --raised: 246 247 247;
  --border: 191 195 197;  --text: 31 35 37;  --muted: 79 87 91;
  --accent: 47 52 55;  --on-accent: 255 255 255;
  --allow: 27 110 55;  --block: 164 38 27;  --ask: 168 71 10;
}
```

`tailwind.config.ts` color map:

```ts
colors: {
  bg: 'rgb(var(--bg) / <alpha-value>)',
  surface: 'rgb(var(--surface) / <alpha-value>)',
  raised: 'rgb(var(--raised) / <alpha-value>)',
  line: 'rgb(var(--border) / <alpha-value>)',
  ink: 'rgb(var(--text) / <alpha-value>)',
  muted: 'rgb(var(--muted) / <alpha-value>)',
  accent: 'rgb(var(--accent) / <alpha-value>)',
  'on-accent': 'rgb(var(--on-accent) / <alpha-value>)',
  allow: 'rgb(var(--allow) / <alpha-value>)',
  block: 'rgb(var(--block) / <alpha-value>)',
  ask: 'rgb(var(--ask) / <alpha-value>)',
}
```

`ThemeProvider.tsx`: stores `'light' | 'dark' | 'black' | 'grey'` in localStorage key `ag-theme`, sets `document.documentElement.dataset.theme`, defaults to system preference. Put a tiny inline script in `index.html` that sets `data-theme` before React loads (prevents flash).

`useThemeColors.ts`: Recharts needs real color strings. Read the CSS variables with `getComputedStyle`, convert `r g b` to `rgb(r,g,b)`, recompute when the theme changes.

Theme switcher: top-bar dropdown, four options, each with a swatch (surface, text, accent), keyboard operable, current theme marked.

## 4. Chart colors

| Series | Token |
|---|---|
| Allowed | `--allow` |
| Blocked | `--block` |
| Ask | `--ask` |
| Normal tasks | `--muted` |
| Grid lines | `--border` |
| Axis text | `--muted` |

Chart marks need 3:1 against `--surface`. Add pattern or direct labels where two series sit close together.

## 5. Layout and sizing

| Property | Value |
|---|---|
| Targets | 1920x1080 (projector, demo video), 1366x768 (minimum laptop) |
| Grid | 12 columns, 16 px gap, 24 px page padding, max width 1920 px |
| Sidebar | 240 px expanded, 64 px collapsed; auto-collapse below 1280 px |
| Top bar | 56 px, sticky |
| Fonts | Inter (UI), JetBrains Mono (logs, hashes, JSON), system fallbacks |
| Sizes | Base 14 px, table 13 px, KPI number 28 px, section title 15 px semibold |
| Cards | Radius 12 px, 1 px `border-line`, 16 px padding, no heavy shadows |
| KPI card | 88 px tall; 6 per row at 1280+, 3 at 1024, 2 below |
| Table rows | 36 px, sticky header, panel scrolls inside its card |
| Touch targets | 36 px minimum, 44 px on tablets |
| Breakpoints | 1536 full, 1280 standard, 1024 sidebar collapsed, under 1024 single column |
| Large mode | Optional setting, base font 16 px, for video and projectors |

Dashboard grid at 1280+:

```
Row 1  [KPI x6, span 2 each]
Row 2  [Live Agent Activity 5] [Pipeline Flow 4] [System Status + Chain Card 3]
Row 3  [Tool Call Timeline 8]  [Attack vs Normal 4]
Row 4  [Live Logs 8]           [Ask Queue + Network Activity 4]
Row 5  [Attack Scenarios 4] [Normal Tasks 4] [Container Resources 4]
```

Log detail opens in a 480 px right drawer so the table stays visible.

## 6. Component rules

- **DecisionBadge**: color + icon + label (`✓ ALLOW`, `✕ BLOCK`, `? ASK`). Tinted background from the `-bg` token.
- **Log rows**: tint with `--*-bg`; click opens the drawer.
- **KpiStrip**: count-up animation (off under `prefers-reduced-motion`); Blocked card flashes once on a new block.
- **ResourceGauges**: bar is normal under 75%, `ask` color above 75%, `block` color above 90%, always with a numeric label.
- **ChainCard**: `allow` "Chain intact" or `block` "Chain broken at entry #N", head hash, entries checked, last verified, Verify now button.
- **AskQueue**: tool, args, reason, risk meter, countdown ("Auto-deny in 0:24"), Approve and Deny. Timeout = deny.
- **SandboxToggle**: confirm dialog before OFF. OFF shows a persistent banner (use `block` color with text and icon) on every page.
- **ConnectionDot**: green live, orange reconnecting (with retry count), red offline; panels show a "stale" label while disconnected.
- **Every panel** has three states: skeleton (loading), friendly empty ("No tool calls yet. Run a scenario."), and error with Retry.

## 7. Accessibility

- Visible focus ring in `--accent` on every interactive element.
- Log region uses polite `aria-live`, announcing only blocks and asks (throttled).
- Respect `prefers-reduced-motion`.
- All icons have accessible labels.
- Minimum 13 px text; Black theme is the high-contrast option for judges far from the screen.

## 8. Review checklist (run before calling any UI done)

- [ ] No blue or purple in any theme, including focus, links, charts
- [ ] No hard-coded hex in components
- [ ] Allow, Block, Ask distinguishable with color removed (icon + label present)
- [ ] All pairings in section 2 measured: 4.5:1 text, 3:1 icons and chart marks
- [ ] All four themes render the page; no flash on reload
- [ ] Hostile strings render as plain text; no `dangerouslySetInnerHTML`
- [ ] Loading, empty and error states exist
- [ ] Looks right at 1920x1080 and 1366x768, plus Large mode
- [ ] Sandbox OFF banner shows on every page
