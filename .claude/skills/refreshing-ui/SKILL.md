---
name: refreshing-ui
description: Build and restyle mySetu AI's React frontend with a clean, refreshing "minimal SaaS" look. Use when adding or editing any component under frontend/src, creating new views, modals, cards, forms, chat elements, or when the user asks to make the UI look fresh/modern/polished, fix spacing, restyle, or theme. Enforces the project's design tokens (yellow SaaS theme), one-CSS-file-per-component convention, animation patterns, and accessibility.
---

# Refreshing UI — mySetu AI Design System

Build interfaces that feel **light, airy, and modern**: soft yellow accent, generous whitespace, rounded corners, subtle shadows, and smooth micro-interactions. Never ship inline magic numbers when a token exists.

## When to use this skill
- Adding/editing any component in `frontend/src/components/`.
- Building a new view, modal, card, form, badge, toast, or chat element.
- The user says "make it look refreshing / modern / cleaner / more polished," asks to fix spacing or alignment, restyle, or re-theme.

## Golden rules (do these every time)
1. **Use design tokens, not literals.** Pull colors, spacing, radius, shadow, and transitions from the CSS variables defined in `frontend/src/index.css` (`:root`). If you need a value that doesn't exist, add a token rather than hardcoding.
2. **One CSS file per component.** `Foo.jsx` imports `./Foo.css`. Keep selectors scoped by a component root class (e.g. `.chat-interface …`). No global element selectors inside a component file.
3. **No CSS frameworks.** This project is plain CSS + React. Do not introduce Tailwind, MUI, styled-components, etc. unless the user explicitly asks.
4. **Mobile-first sanity.** Respect the existing `@media (max-width: 768px)` / `480px` breakpoints; test that nothing overflows `overflow-x: hidden`.
5. **Animate with intent.** Entrances use `fadeIn`/`fadeInUp` (0.3–0.5s ease-out); hovers use `translateY(-1px to -2px)` + shadow lift over `--transition-base`. Keep it subtle.
6. **Accessibility:** real `<button>`/`<label>`/`<input>` elements, `alt` on images, visible focus rings (yellow glow), `title`/`aria-label` on icon-only buttons, sufficient contrast (dark text `#1F2937` on yellow, never light-on-yellow).

## Design tokens (source of truth: `index.css`)

**Brand / accent**
```
--saas-yellow: #FACC15;          /* primary accent (buttons, active states) */
--saas-yellow-hover: #FBBF24;    /* hover/darker accent */
--saas-yellow-tint: #FFF9E6;     /* page background, soft hover fills */
--saas-green: #22C55E;           /* success / "system safe" */
--saas-orange: #FB923C;          /* warning */
--saas-red: #EF4444;             /* error (softened) */
--color-accent-gradient: linear-gradient(135deg, #FACC15 0%, #FBBF24 100%);
```

**Text**
```
--color-text-primary:   #1F2937;   /* headings, body */
--color-text-secondary: #6B7280;   /* supporting copy */
--color-text-muted:     #9CA3AF;   /* hints, timestamps */
--color-text-on-accent: #111827;   /* ALWAYS dark text on yellow */
```

**Surfaces / borders**
```
--color-bg-page:      #FFF9E6;   /* app background (warm) */
--color-bg-secondary: #FFFFFF;   /* cards, panels, content area */
--color-bg-tertiary:  #F9FAFB;   /* inputs, recessed fills */
--color-border:       #E5E7EB;
```

**Radius** `--radius-sm .375rem` · `md .625rem` · `lg .875rem` · `xl 1.125rem` · `2xl 1.5rem` · `full 9999px`
**Spacing** `--spacing-xs .25` · `sm .5` · `md 1` · `lg 1.5` · `xl 2` · `2xl 3` (rem)
**Shadow** `--shadow-xs/sm/md/lg/xl`, plus `--shadow-card` for resting cards and `--shadow-glow` for accent emphasis.
**Transitions** `--transition-fast 140ms` · `--transition-base 230ms` · `--transition-slow 360ms` (all `cubic-bezier(.4,0,.2,1)`).
**Font** `--font-family` = Inter (loaded via Google Fonts in `index.css`). Sizes `--font-size-xs … 4xl`.

> The file also keeps legacy `--ms-blue*` aliases mapped onto yellow for backwards compatibility — prefer the `--saas-*` / `--color-*` names in new code.

## The "refreshing" recipe
Apply these to make any surface feel fresh:
- **Whitespace first:** pad cards `--spacing-lg`+, gap lists with `--spacing-sm`–`md`. Crowded UI never feels fresh.
- **Soft elevation:** white cards on the warm `--color-bg-page`, `--shadow-card` at rest, lift to `--shadow-lg` + `translateY(-2px)` on hover.
- **Rounded everything:** `--radius-xl` for cards, `--radius-full` for pills/inputs/avatars-as-circles, `--radius-md` for small chips.
- **One confident accent:** yellow for the *primary* action only. Secondary actions are bordered/ghost. Don't paint everything yellow.
- **Micro-motion:** `animate-fade-in-up` on mount; hover lifts; `--transition-base` on interactive states.
- **Glassy headers (optional):** `.glass-effect` utility for sticky/overlay bars.

## Copy-paste patterns

**Primary button**
```css
.btn-primary {
  background: var(--saas-yellow);
  color: var(--color-text-on-accent);
  font-weight: 600;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}
.btn-primary:hover { background: var(--saas-yellow-hover); transform: translateY(-1px); box-shadow: var(--shadow-md); }
.btn-primary:disabled { opacity: .45; cursor: not-allowed; transform: none; }
```

**Card**
```css
.surface-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-base);
}
.surface-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
```

**Input / focus ring**
```css
.field {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}
.field:focus { border-color: var(--saas-yellow); box-shadow: 0 0 0 3px rgba(250,204,21,.18); }
```

**Pill / badge** — reuse global `.badge`, `.badge-success|warning|error|info`. For status chips use `--radius-full`, `--font-size-xs`, weight 600.

**Active nav item** (Sidebar pattern): light yellow tint fill (`rgba(250,204,21,.15)`), inset `3px` yellow left border, icon `scale(1.05)`, `translateX(2px)` on hover.

**Entrance animation:** add `className="animate-fade-in-up"` (defined globally) or, for lists, stagger with `animation-delay`.

## Component conventions in this codebase
- **Chat bubbles:** user = yellow bubble right-aligned with asymmetric radius (`18px 18px 4px 18px`); assistant = white card left-aligned (`4px 18px 18px 18px`), 38px rounded-square avatar.
- **Markdown answers** render via `react-markdown` inside `.markdown-body` — style headings/lists/code/blockquote there (yellow custom bullets, dark code blocks, yellow blockquote bar).
- **Streaming cursor:** append `<span className="streaming-cursor" />` while `isStreaming`.
- **Typing indicator:** three dots that pulse gray→yellow (`.typing-indicator span`).
- **Sources & confidence:** sources render as `.source-item` pills with a relevance %; confidence shows a colored dot (`.confidence-dot` → green ≥0.7, `medium` ≥0.4, else `low`).
- **Modals:** overlay = `rgba(0,0,0,.4)` + `backdrop-filter: blur(4px)`; panel = white, `--radius-2xl`, `--shadow-xl`, `fadeInUp` entrance; close on overlay click but `stopPropagation` on the panel.
- **Status pills (Header):** green tint + pulsing dot for healthy, amber for warning, red for critical (`getStatusColor`/`getStatusText` pattern).

## Workflow when restyling or adding UI
1. Read the component's existing `.jsx` and `.css` to match its idiom (class naming, spacing rhythm).
2. Reuse global utilities (`.card`, `.badge`, `.spinner`, `.glass-effect`, `animate-*`) before writing new CSS.
3. Express new values as tokens; only add a `:root` variable if genuinely missing.
4. Keep the JSX semantic and the CSS scoped under the component root class.
5. Verify hover/focus/disabled/empty/loading states all exist and use transitions.
6. Check responsiveness at 768px and 480px.

## Anti-patterns (reject these)
- Hardcoded hex colors / px shadows / ad-hoc transition timings when a token exists.
- Light/white text on a yellow background (fails contrast — use `--color-text-on-accent`).
- Painting multiple competing accent colors; yellow is the single hero accent.
- Inline `style={{…}}` for anything reusable (small one-offs like `display:none` view toggles are acceptable, matching `App.jsx`).
- Introducing a CSS framework or component library unprompted.
- Removing focus outlines without providing a visible alternative.
</content>
