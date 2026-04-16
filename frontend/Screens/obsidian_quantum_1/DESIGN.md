# Design System Document: The Quantitative Ethereal

## 1. Overview & Creative North Star
**Creative North Star: The Sovereign Intelligence**
The design system for CFO.ai moves away from the "cluttered spreadsheet" archetype of traditional fintech. Instead, it adopts a high-end editorial aesthetic that treats financial data as a narrative. We aim for "The Sovereign Intelligence"—a look that feels authoritative, calm, and predictive. 

By leveraging intentional asymmetry, expansive negative space, and a sophisticated layering of translucent surfaces, we transform dense data into an "Ethereal Dashboard." We break the standard grid by using overlapping "glass" containers and high-contrast typography scales, ensuring the AI’s insights feel like a premium concierge service rather than a basic software tool.

---

## 2. Colors & Surface Logic
The palette is rooted in deep obsidian tones, punctuated by high-chroma accents that signify fiscal health.

### Surface Hierarchy & Nesting
We reject the "flat" web. Depth is our primary navigator. Use the `surface-container` tiers to create a physical sense of "stacking."
*   **Base Layer:** `surface` (#111319) is your canvas.
*   **Sectioning:** Use `surface_container_low` (#191b22) for large structural areas like sidebars or footer regions.
*   **Primary Interaction:** Use `surface_container_high` (#282a30) for the main dashboard cards.
*   **The "No-Line" Rule:** Explicitly prohibit the use of 1px solid borders to define sections. Boundaries must be established through color shifts or tonal transitions. If two areas are adjacent, one must be a different surface tier.

### The Glass & Gradient Rule
To achieve the "AI" feel, the topmost interactive layers (modals, dropdowns, floating insights) must use **Glassmorphism**. 
*   **Formula:** `surface_container_highest` at 60% opacity + `backdrop-blur: 12px`.
*   **Signature Textures:** Apply a subtle linear gradient to primary CTAs: `primary` (#c3c0ff) to `primary_container` (#4f46e5) at a 135-degree angle. This adds "soul" to the action buttons.

---

## 3. Typography
We utilize **Inter** to maintain a surgical, modern precision. The hierarchy is designed to highlight "The Number" while keeping meta-data subservient.

*   **Display Scales (LG/MD):** Reserved for hero metrics (e.g., Total Runway, Net Burn). These should feel like headlines in a premium financial journal.
*   **Headline Scales:** Used for section titles. Pair these with high-contrast `on_surface` (White) to command attention.
*   **Label Scales (MD/SM):** Use `on_surface_variant` (#c7c4d8) for labels. These are intentionally muted to let the data (the numbers) breathe.
*   **Intentional Weighting:** Never use "Bold" for body text. Stick to Regular or Medium. Reserve Semi-Bold only for `title-sm` and `label-md` to ensure a sophisticated, light-touch feel.

---

## 4. Elevation & Depth
In this system, light is the architect. We do not use "shadows" in the traditional sense; we use **Ambient Illumination.**

*   **The Layering Principle:** A card should feel like it is floating 10mm above the surface. Place a `surface_container_highest` card on a `surface_dim` background. The contrast is the border.
*   **Ambient Shadows:** For floating elements (Modals/Popovers), use an extra-diffused shadow: `box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4)`. The shadow should not be grey; it should be a darker version of the background color to mimic natural light absorption.
*   **The "Ghost Border" Fallback:** If a container requires more definition (e.g., for accessibility in data tables), use a "Ghost Border": `outline_variant` at 15% opacity. It should be felt, not seen.

---

## 5. Components

### Buttons
*   **Primary:** Gradient fill (`primary` to `primary_container`), `md` (0.375rem) roundedness. No border. Text is `on_primary_fixed`.
*   **Secondary:** Ghost style. Transparent background with a `Ghost Border`. Text is `primary`.
*   **Tertiary:** Text-only with an underline appearing only on hover.

### Cards & Lists (The Financial Narrative)
*   **The Card Rule:** No dividers. Use **Vertical White Space** (Spacing `8` or `10`) to separate line items. 
*   **Data Rows:** Instead of lines, use a subtle hover state: `surface_bright` at 5% opacity to highlight the active row.
*   **Glass Cards:** For AI-generated insights, use a `surface_container_highest` with a `backdrop-blur` and a 1px "Ghost Border" at the top edge only to simulate a light reflection.

### Chips (Metric Indicators)
*   **Positive/Growth:** Text `emerald`, background `emerald` at 10% opacity.
*   **Negative/Burn:** Text `coral`, background `coral` at 10% opacity.
*   **Style:** `full` (9999px) roundedness for a pill-shaped, friendly appearance.

### Input Fields
*   **Resting State:** `surface_container_lowest` with a subtle `outline_variant` (20% opacity).
*   **Active/Focus:** Border transitions to `primary` with a 2px outer glow (ambient shadow) of the same color.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** embrace asymmetry. If you have three cards, let one be 66% width and the others 33% to create an editorial flow.
*   **Do** use `letter-spacing: -0.02em` on all Display and Headline typography to give it a "tight," custom-printed look.
*   **Do** use the Spacing Scale religiously. Consistent gaps of `4` (0.9rem) or `6` (1.3rem) are what separate a pro dashboard from a template.

### Don't:
*   **Don't** use pure black (#000000). It kills the depth of the "Ethereal" glass effect.
*   **Don't** use 100% opaque borders. They create "visual noise" that fatigues the user during long sessions of data analysis.
*   **Don't** use icons as purely decorative elements. Every icon must serve a functional purpose or highlight a specific AI insight.
*   **Don't** use standard "Drop Shadows" on cards that are already resting on a surface. Use tonal shifts instead.