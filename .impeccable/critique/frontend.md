---
target: frontend
total_score: 16
p0_count: 0
p1_count: 3
timestamp: 2026-07-03T06-52-00Z
slug: frontend
---
⚠️ DEGRADED: single-context (spawn_agent unavailable in this session)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | The stage flow is visible, but system health and dependency failure are not surfaced clearly when backend capability requests wobble. |
| 2 | Match System / Real World | 2 | The product language is mostly domain-correct, but the arrival experience still behaves more like a product site than a research instrument. |
| 3 | User Control and Freedom | 2 | Reset exists and staged navigation is clear, but users still get trapped in brittle states caused by hidden backend dependence. |
| 4 | Consistency and Standards | 1 | Header pills, stage shells, side navigation, metrics, and form controls still do not read as one stable system. |
| 5 | Error Prevention | 1 | The UI allows users into states where dropdowns appear empty or surfaces partially load without clear causality. |
| 6 | Recognition Rather Than Recall | 2 | The stage model helps, but the quantity of labels, framed sections, and support text still asks users to re-parse too much. |
| 7 | Flexibility and Efficiency | 1 | Expert users still get a ceremonial workflow rather than a compact analytical workbench. |
| 8 | Aesthetic and Minimalist Design | 1 | The design remains visually over-boxed and structurally repetitive. |
| 9 | Error Recovery | 1 | When services fail or become stale, the UI gives poor recovery guidance and fragile reassurance. |
| 10 | Help and Documentation | 3 | The guide surface and stage copy are present and understandable. |
| **Total** | | **16/40** | **Weak: coherent intent, unstable execution** |

#### Anti-Patterns Verdict

**LLM assessment**: This still looks like an interface trying to be three things at once: landing page, staged workflow shell, and research control surface. The result is recognizably AI-shaped, not because of gradients or gimmicks, but because the structure is still composed of familiar generated patterns stacked together without enough ruthless editing. The product says “credible research tool,” but the interface still spends too much surface area narrating itself.

**Deterministic scan**: `detect.mjs --json frontend` returned `[]` again. That is another false clean. The scan is not catching the actual quality failures because the main defects are systemic: component inconsistency, over-framing, brittle control behavior, and poor recovery states when the backend becomes unstable.

**Visual overlays**: No reliable user-visible overlay was produced. Browser inspection succeeded on `http://127.0.0.1:5173/`, `#tool`, and `#architecture`, but mutable script injection could not be verified in this session because the available browser-evaluation path is read-only. Fallback signal used: direct screenshots plus DOM snapshots of the live UI.

#### Overall Impression
The app is more visually restrained than before, but it is still not behaving like a trustworthy product tool. The biggest problem is no longer the palette. It is that the surface looks calm while the interaction model remains brittle and over-structured.

#### What's Working
- The color system is closer to the intended tone. It reads warmer and less like generic dark AI tooling.
- The staged workflow is conceptually appropriate for this domain. Circuit -> architecture -> estimation -> results is legible.
- The domain copy is materially more specific than template SaaS language. It names the actual analytical job.

#### Priority Issues
- **[P1] The product still has no settled operating surface**
  - **Why it matters**: A research tool earns trust by disappearing into the task. This UI still foregrounds shells, kickers, and framing instead of the analytical controls themselves.
  - **Fix**: Strip back the repeated header pills, redundant stage framing, and card-like segmentation until the main work areas carry the hierarchy.
  - **Suggested command**: `$impeccable distill`
- **[P1] Backend instability is leaking into the UI without honest recovery states**
  - **Why it matters**: Empty dropdowns, partial architecture state, and backend-dependent surfaces that silently wobble are catastrophic for trust in a scientific tool.
  - **Fix**: Add explicit dependency-failure states, route-level recovery messaging, and non-ambiguous loading/error handling for architecture and capability fetches.
  - **Suggested command**: `$impeccable harden`
- **[P1] The architecture workflow still feels patched rather than designed**
  - **Why it matters**: This is the key trust surface, and it still shows spacing regressions, brittle control sizing, and too much explanatory framing around the core fields.
  - **Fix**: Rework the architecture card as one deliberate control surface with stable row logic, consistent field shells, and fewer stacked explanatory blocks.
  - **Suggested command**: `$impeccable layout`
- **[P2] The landing page is still too promotional for a local expert tool**
  - **Why it matters**: The first screen still behaves like a marketing hero when the product’s real value is its working environment.
  - **Fix**: Compress the landing layer into a terse handoff to the workspace or a serious overview panel, not a persuasion page.
  - **Suggested command**: `$impeccable shape`
- **[P2] Component vocabulary is still too repetitive and box-heavy**
  - **Why it matters**: When every section, note, summary, and metric gets its own framed container, nothing feels important and everything feels generated.
  - **Fix**: Reduce container count, simplify secondary surfaces, and reserve bordered treatments for genuinely interactive or decision-critical regions.
  - **Suggested command**: `$impeccable quieter`

#### Persona Red Flags
- **Mira (quantum researcher comparing hardware assumptions)**: The architecture screen still reads as visually calm but operationally fragile. If presets disappear or half-load, she will not trust any output derived from that state.
- **Alex (power user)**: The tool consumes too much vertical and cognitive space before he can act. Sidebar workflow framing, repeated labels, and oversized stage headers slow down repeat usage.
- **Jordan (first-timer)**: The workflow is understandable, but the system does not explain failures well. A blank or unstable architecture control looks like a broken product, not a learnable one.

#### Minor Observations
- The top nav still feels more like brochure navigation than tool navigation.
- The “idle” footer state is too low-signal to help users understand whether the system is actually ready.
- The architecture and topology panes still look more like adjacent cards than one coordinated working area.
- Buttons are calmer than before, but disabled and secondary states still feel under-resolved.

#### Questions to Consider
- If the backend disappeared for ten seconds, what would a truthful version of this interface say and show?
- Which parts of the current shell are helping the analysis workflow, and which parts are simply explaining that a workflow exists?
- If you removed the landing page entirely, would the product become clearer or less clear?
