# Terra Design System

## Identity

The application uses a warm, grounded product palette that keeps a research workflow calm and readable instead of dark, futuristic, or aggressively technical.

## Color

### Palette

- `--bg`: `#faf6f0`
- `--bg-deep`: `#efe7dc`
- `--bg-panel`: `#fffaf4`
- `--bg-panel-2`: `#f4ede3`
- `--bg-panel-3`: `#e8dccb`
- `--text`: `#233127`
- `--text-soft`: `#5f6d61`
- `--text-muted`: `#728074`
- `--line`: `#d8ccbd`
- `--line-strong`: `#bda98d`
- `--primary`: `#4a7c59`
- `--primary-strong`: `#3f6b4c`
- `--tertiary`: `#705c30`
- `--success`: `#4f8a62`
- `--warning`: `#8d6930`
- `--error`: `#9f5f52`

### Usage

- Warm cream backgrounds should carry the full app shell.
- Green is reserved for primary actions, navigation emphasis, and active states.
- Amber-brown is used as a restrained secondary accent for highlights and warnings.
- Neutrals should stay warm and slightly organic; avoid cold grays and high-contrast blue blacks.

## Typography

- Keep the current application typography unchanged for now.
- Future iterations can adopt the Terra direction:
  - Headlines: `Literata`
  - Body and labels: `Nunito Sans`

## Elevation

- Favor tonal separation over heavy shadows.
- Use soft borders and low-contrast surfaces instead of dark translucent panels.
- Keep shadows subtle and rare.

## Components

- Primary buttons use solid green with light text.
- Secondary controls use cream-toned surfaces with green text or warm neutral borders.
- Cards, panels, and inputs stay light, soft, and readable.
- Status chips and callouts should use tinted semantic fills instead of dark glass surfaces.

## Constraints For This Pass

- This pass changes color only.
- Do not change layout, spacing, component structure, typography, or interaction patterns.
- Preserve existing UI composition while migrating the surface palette across the entire app.
