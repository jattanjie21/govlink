# GovLink — Design Deliverable

National data platform for The Gambia. Editorial-authoritative visual
system, deep teal `#0F4C5C` on warm canvas `#FAF8F4`, Fraunces display +
Geist body + JetBrains Mono code. Light primary, dark toggle on every
page. Responsive at 1440 / 768 / 375.

This is the HTML reference design. Every screen is standalone and self-
contained — open any `.html` file directly in a browser, no build step.
The system is documented in `style-guide.html` and `components.html`,
mapped to React/Tailwind/shadcn in `handoff.html`, and exported as code
tokens in `tokens.css` and `tailwind.config.ts`.

---

## Engineering quick start

1. Drop `tokens.css` at the top of your global stylesheet.
2. Replace the placeholder `tailwind.config.ts` in your Vite/Next project
   with the one shipped here.
3. Read `handoff.html` for the per-component shadcn primitive mapping
   and the recommended file layout.
4. Use `components.html` as the visual contract while implementing — every
   component there shows default / hover / focus / active / disabled /
   loading + empty/error states.

Theme is controlled by `<html data-theme="light|dark">`. The theme
toggle pattern in every screen persists to `localStorage['govlink-theme']`.

---

## Screens — canonical entry order

### Public site (8)

Reviewer's path: open in this order to walk the user journey end-to-end.

| #  | File                          | Purpose                                                     |
| -- | ----------------------------- | ----------------------------------------------------------- |
| 1  | `index.html`                  | Home — hero, featured datasets, latest reports, dev strip   |
| 2  | `browse.html`                 | Browse datasets — search + faceted sidebar + result cards   |
| 3  | `dataset-detail.html`         | Dataset detail — Overview tab (the most important screen)   |
| 4  | `dataset-api.html`            | Dataset → API tab — endpoints, params, code in 4 languages  |
| 5  | `reports.html`                | Reports index — editorial magazine layout                   |
| 6  | `report-read.html`            | Report read view — long-form article + embedded charts      |
| 7  | `developer.html`              | Developer landing — API keys, quotas, getting started       |
| 8  | `auth.html`                   | Login / register / profile (tabbed)                         |

### Admin dashboard (7)

Same design system, denser layout. Shared `admin-` prefix and a
shared left-sidebar chrome.

| #  | File                              | Purpose                                                     |
| -- | --------------------------------- | ----------------------------------------------------------- |
| 9  | `admin-overview.html`             | Admin home — KPI strip, ingestion queue, alerts feed        |
| 10 | `admin-ingestion-wizard.html`     | 6-step ingestion — upload → schema → metadata → publish     |
| 11 | `admin-ingestion-job.html`        | Live ingestion job — pipeline stepper + streaming logs      |
| 12 | `admin-dataset-insights.html`     | Data-owner view — calls/downloads, geo, top consumers       |
| 13 | `admin-reports-editor.html`       | Markdown editor + live preview + dataset-embed inserter     |
| 14 | `admin-users.html`                | Users + organizations + API keys (tabbed)                   |
| 15 | `admin-settings.html`             | Categories, licenses, featured items, platform config       |

### System artifacts (5)

| #  | File                  | Purpose                                                              |
| -- | --------------------- | -------------------------------------------------------------------- |
| 16 | `style-guide.html`    | Tokens, type scale, color ramps, motion, voice, accessibility audit  |
| 17 | `components.html`     | Component library — every component × every state                    |
| 18 | `handoff.html`        | Engineering handoff — shadcn mapping, Tailwind notes, file layout    |
| 19 | `brand-assets.html`   | Wordmark, mark, favicon set, OG image, do's & don'ts                 |
| 20 | `command-palette.html`| Cmd+K palette demo (referenced in nav across all screens)            |

### Source files

| File                  | Purpose                                                              |
| --------------------- | -------------------------------------------------------------------- |
| `brand-spec.md`       | Authoritative token + voice spec (the source these files derive from)|
| `tokens.css`          | All design tokens as CSS custom properties — drop into global.css    |
| `tailwind.config.ts`  | Tailwind theme extension wired through the CSS variables             |
| `README.md`           | This file                                                            |

---

## Older artifact copies — safe to delete

These are duplicates from earlier turns that the canonical files
superseded. The harness keeps them around as historical artifacts.

- `govlink-home.html`              → use `index.html`
- `govlink-report-read.html`       → use `report-read.html`
- `govlink-dataset-insights.html`  → use `admin-dataset-insights.html`

---

## What's not shipped here

The brief asked for some artifacts HTML can't produce. These are
called out so engineering and design know what's still owed:

- **Figma file** — tokens, component library, all screens at 3
  breakpoints, light + dark. The visual system is fully specified in
  HTML; a Figma rebuild is a straight port.
- **Binary asset exports** — `.svg` wordmark/mark, `.ico` favicon set,
  `.png` OG card. `brand-assets.html` shows them all rendered; the
  files themselves need to be exported from a vector tool.
- **Recharts wiring** — the charts in `report-read.html` and
  `admin-dataset-insights.html` are hand-authored SVG. They'll be
  re-implemented in Recharts during the React build; the visual
  contract is set, the JSX isn't.
- **Tablet (768) eyeball pass** — responsive rules are written across
  all 19 screens but haven't been verified at that breakpoint.
- **Dark-mode contrast audit** — the toggle works everywhere, but the
  data-viz palettes (sequential ramp, categorical 5-color) need a
  dedicated WCAG AA pass against the dark canvas.

---

## Conventions

- **Dates**: `DD MMM YYYY` (e.g., `02 May 2025`).
- **Currency**: GMD.
- **Country code**: GM.
- **Tabular numerals**: `font-variant-numeric: tabular-nums` on every
  numeric value. Non-negotiable for tables and KPI cards.
- **No zebra striping**. Tables use rule lines top + bottom and a hairline
  between rows.
- **Spacing**: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96. No values
  outside this scale.
- **Radii**: 0 (rules), 2 (chips), 4 (inputs/buttons), 6 (cards), 8
  (modals). Nothing larger. No squircles.
- **Anti-patterns**: see `style-guide.html` and the bottom of
  `brand-spec.md`. Most-violated to watch for: purple gradients,
  glassmorphism, Inter as a *display* face, flag colors as palette,
  Bootstrap-bright status colors.
