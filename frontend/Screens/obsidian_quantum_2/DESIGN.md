# Design System Specification: Sovereign Intelligence

## 1. Overview & Creative North Star
This design system is built upon the Creative North Star of **"Sovereign Intelligence."** In the high-stakes world of AI-driven finance, the UI must feel like a digital private office—quiet, authoritative, and impossibly sharp. We are moving away from the "busy dashboard" aesthetic toward an **Editorial Financial Experience**. 

The system breaks traditional "template" layouts by utilizing intentional asymmetry, deep tonal layering, and high-contrast typography scales. By leveraging the "Obsidian Quantum" aesthetic, we create a sense of vast depth through dark surfaces, where data isn't just displayed—it is revealed through soft glows and frosted glass transitions.

---

## 2. Colors & Surface Philosophy
The palette is rooted in deep obsidian tones, punctuated by the "Quantum" energy of indigo and emerald.

### Palette Application
- **Primary (`#c3c0ff` / `#4f46e5`):** Reserved for core brand actions and high-level financial projections.
- **Secondary (`#4edea3` / `#10b981`):** Used strictly for "Growth," "Liquidity," and "Positive Delta." It is the pulse of the platform.
- **Surface & Background (`#111319`):** The foundation. It is a true charcoal-navy that provides the "Sovereign" weight.

### The "No-Line" Rule
To achieve a premium, seamless feel, **1px solid borders are prohibited for sectioning.** Structural boundaries must be defined through:
- **Tonal Shifts:** Placing a `surface-container-high` card against a `surface-container-lowest` background.
- **Negative Space:** Using the Spacing Scale (e.g., `spacing-12` or `16`) to create architectural "voids" that separate data modules.

### Surface Hierarchy & Nesting
Think of the UI as physical layers of obsidian glass.
- **Foundation:** `surface` (#111319)
- **Primary Sections:** `surface-container-low` (#191b22)
- **Nested Components (Cards/Modals):** `surface-container-high` (#282a30)
- **Interactive Elements:** `surface-container-highest` (#33343b)

### The Glass & Gradient Rule
For hero elements and primary CTAs, use a subtle linear gradient transitioning from `primary_container` (#4f46e5) to `primary` (#c3c0ff) at a 135-degree angle. Floating panels should employ **Glassmorphism**: a semi-transparent `surface_container` with a `backdrop-filter: blur(20px)`.

---

## 3. Typography
We use **Inter** exclusively. Its neutrality allows the financial data to remain the protagonist.

| Level | Token | Size | Weight | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | 3.5rem | 600 | Hero metrics, Portfolio Totals. |
| **Headline** | `headline-sm` | 1.5rem | 500 | Section headers, "Quantum Analysis" titles. |
| **Title** | `title-md` | 1.125rem | 600 | Card titles, Modal headers. |
| **Body** | `body-md` | 0.875rem | 400 | General financial insights and reports. |
| **Label** | `label-sm` | 0.6875rem | 700 | Uppercase with 5% letter spacing. For metadata. |

**Editorial Note:** Use high contrast between `display-lg` and `label-sm` to create a sophisticated, magazine-like hierarchy. Avoid "mid-range" font sizes where possible to keep the layout feeling intentional.

---

## 4. Elevation & Depth
Depth is not achieved through shadows, but through **Tonal Layering**.

- **The Layering Principle:** Rather than "lifting" an object with a shadow, "carve" it out of the background using the surface tiers. A `surface-container-lowest` section sitting inside a `surface-container-low` area creates a "sunken" or "embedded" look, perfect for data input fields.
- **Ambient Shadows:** For floating elements (modals/tooltips), use a highly diffused shadow: `0px 24px 48px rgba(0, 0, 0, 0.4)`. The shadow should feel like a soft ambient occlusion, not a hard drop shadow.
- **The "Ghost Border" Fallback:** If a divider is mandatory for accessibility, use the `outline_variant` (#464555) at **15% opacity**. It should be felt, not seen.
- **Fine-Lined Grids:** Incorporate a subtle 24px background grid using `outline_variant` at 5% opacity to evoke a sense of precision and "Quantum" calculation.

---

## 5. Components

### Buttons
- **Primary:** Gradient fill (`primary_container` to `primary`), `8px` (lg) corner radius. Use a soft `primary` outer glow (4px blur) on hover.
- **Secondary:** Transparent background with a "Ghost Border" (`outline_variant` at 20%).
- **Tertiary:** Text-only using `primary_fixed_dim`.

### Input Fields
- **Styling:** Use `surface_container_lowest` for the field background. No borders.
- **Focus State:** Transition the background to `surface_container_high` and add a 1px soft glow using `primary` at 30% opacity.
- **Radii:** Always use `DEFAULT` (4px) for a sharper, more professional look.

### Cards & Lists
- **No Divider Lines:** Use `spacing-4` or `spacing-6` between list items.
- **Interactive State:** On hover, a card should shift from `surface-container-low` to `surface-container-high`.
- **"Quantum" Chips:** Use `secondary_container` (#00a572) for positive growth indicators, paired with `on_secondary_container` text. Keep the radius `full` (9999px) for chips only.

### Contextual Intelligence (AI Insights)
- **Component:** A frosted glass panel (`backdrop-blur: 12px`) with a subtle `primary` glow emanating from the top-left corner to signify "AI Activity."

---

## 6. Do's and Don'ts

### Do:
- **Do** use `secondary` (Emerald) sparingly. It should indicate "Value" or "Success" and nothing else.
- **Do** utilize asymmetrical layouts—e.g., a large metric on the left balanced by white space and a small label on the right.
- **Do** use `surface-container-highest` for active states in navigation.

### Don't:
- **Don't** use pure black (#000000). The deepest tone should always be `surface_container_lowest` (#0c0e14).
- **Don't** use 100% opaque borders. They break the "Obsidian Quantum" fluidity.
- **Don't** use standard "Success/Warning/Error" colors if they clash with the palette. Use `error` (#ffb4ab) with low saturation to maintain the sophisticated atmosphere.