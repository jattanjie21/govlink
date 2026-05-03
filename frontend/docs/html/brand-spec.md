# GovLink — Brand Spec

National data platform for The Gambia. Editorial-authoritative — sits next
to a serious newspaper's data section, a central bank research portal, or a
UN statistical office. Not techy-startup, not stereotypically "African dev
project."

## Color

### Light (primary)

| Token              | Value      | Use                                                      |
| ------------------ | ---------- | -------------------------------------------------------- |
| `--canvas`         | `#FAF8F4`  | Page background. Warm paper, not pure white.             |
| `--surface`        | `#FFFFFF`  | Cards, dropdowns, code blocks (when inverted).           |
| `--surface-2`      | `#F2EFE8`  | Sidebars, faint banding, footer.                         |
| `--ink`            | `#1A1A1A`  | Primary text, headlines.                                 |
| `--ink-2`          | `#3D3D3D`  | Secondary text, body labels.                             |
| `--ink-3`          | `#6B6B6B`  | Muted, captions, table column headers.                   |
| `--rule`           | `#E5E2DA`  | Subtle borders, table rules.                             |
| `--rule-2`         | `#D5D0C4`  | Stronger borders, focused inputs.                        |
| `--accent`         | `#0F4C5C`  | Primary action, link hover, active tab. Used sparingly.  |
| `--accent-hover`   | `#0A3A47`  | Pressed / hover on accent.                               |
| `--accent-tint`    | `#E5EFF1`  | Active-tab background, link-rest underline tint.         |
| `--success`        | `#2F6B3D`  | Forest green. Status pills, verified.                    |
| `--warning`        | `#B27800`  | Ochre. Schema null-% pills, soft alerts.                 |
| `--danger`         | `#A03B2C`  | Rust red. Destructive only.                              |

### Dark (secondary, toggle on every page)

| Token              | Value      |
| ------------------ | ---------- |
| `--canvas`         | `#141312`  |
| `--surface`        | `#1C1B19`  |
| `--surface-2`      | `#222020`  |
| `--ink`            | `#F0EDE6`  |
| `--ink-2`          | `#C0BBB0`  |
| `--ink-3`          | `#8A867D`  |
| `--rule`           | `#2A2826`  |
| `--rule-2`         | `#3A3835`  |
| `--accent`         | `#5FB8CC`  |
| `--accent-hover`   | `#7CCCDF`  |
| `--accent-tint`    | `#1F3A40`  |
| `--success`        | `#5CA374`  |
| `--warning`        | `#D8A33A`  |
| `--danger`         | `#D17265`  |

### Data-viz

Sequential ramp (5 stops) anchored on `--accent`:
`#CFE0E5 · #93BCC4 · #4F8E9C · #0F4C5C · #093642`

Categorical (6, distinct in both light & dark, AA on `--canvas`):
`#0F4C5C · #B27800 · #6B4F8C · #2F6B3D · #A03B2C · #4A4A4A`

## Type

- **Display**: Fraunces, weights 400 / 600. Optical size 144 (`opsz=144`)
  on hero numbers and dataset titles ≥ 32px.
- **Body / UI**: Geist (with Inter Tight fallback). 400 / 500 / 600.
- **Mono**: JetBrains Mono. 400 / 500. Used for code, IDs, tabular IDs in
  admin tables.
- **Tabular numerals**: `font-variant-numeric: tabular-nums` on every
  table cell, KPI value, and meta strip number. Non-negotiable.

### Scale (8 steps)

| Token            | Size  | Line-height | Use                                       |
| ---------------- | ----- | ----------- | ----------------------------------------- |
| `--text-eyebrow` | 11px  | 1.25        | Uppercase eyebrows / kickers.             |
| `--text-xs`      | 12px  | 1.4         | Captions, footnotes.                      |
| `--text-sm`      | 13px  | 1.5         | Table cells, meta strips, labels.         |
| `--text-base`    | 15px  | 1.6         | Default body.                             |
| `--text-md`      | 17px  | 1.55        | Lead paragraphs, card titles.             |
| `--text-lg`      | 21px  | 1.4         | Section heads, dataset card titles.       |
| `--text-xl`      | 32px  | 1.2         | Page titles.                              |
| `--text-display` | 56px  | 1.05        | Hero / dataset hero (Fraunces).           |

## Spacing

`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96`. No values outside this scale.

## Radii

`0 (rules) · 2 (chips) · 4 (inputs, buttons) · 6 (cards) · 8 (modals)`.
Nothing larger. No squircles.

## Layout

- 12-col grid, 1200px content max (1440 viewport: 120px outer margins).
- Tablet (768): 8-col grid, 32px outer.
- Mobile (375): 1-col, 20px outer.
- Tables: rule lines top + bottom, hairline rules between rows. **No
  zebra striping.** Tabular numerals.
- Vertical rhythm: 8px baseline.

## Motion

- `--ease`:    `cubic-bezier(0.2, 0, 0, 1)`
- `--ease-in`: `cubic-bezier(0.4, 0, 1, 1)`
- `--dur-1`: 120ms (focus ring, instant)
- `--dur-2`: 180ms (hover, fade)
- `--dur-3`: 280ms (page-load fade)
- Hero stagger: 40ms between hero elements on initial load.
- No bouncing. No parallax. No flourish for its own sake.

## Voice / national nod

A single accent stripe in the footer (red · navy-substitute · forest-green
order, 1px each, 8px total) is the *only* permitted nod to flag colors.
Wordmark uses Fraunces — the serif echoes official documents without
leaning into government-website cliché.

Real Gambian context throughout: Banjul, Kanifing, West Coast Region,
Brikama, Basse, Janjanbureh; Ministry of Finance, Health, Basic and
Secondary Education; GBoS as recurring publisher; UNDP / UNICEF / WHO /
WB / AfDB Gambia. Dates `DD MMM YYYY`. Currency `GMD`. Country `GM`.

## Anti-patterns (audit before shipping)

- ❌ Purple gradient hero
- ❌ Glassmorphism / soft squircles
- ❌ Hero video, parallax, bouncing micro-interactions
- ❌ Inter / Roboto / Arial as the *display* face
- ❌ Stock African-development imagery
- ❌ Heavy flag-as-UI palette
- ❌ Generic emoji feature icons
- ❌ Rounded card with left-border accent
- ❌ Zebra-striped tables
- ❌ Bootstrap-bright status colors
