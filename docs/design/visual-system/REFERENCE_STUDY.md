# Reference Study

## Purpose

This study defines what Athanor should adopt and avoid from external systems before any new tokens or styles are implemented.

The goal is not to imitate another product. The goal is to extract durable design rules from strong official systems and apply them to Athanor's operator context.

## Core conclusion

Athanor should combine:

- Carbon's layered neutral discipline
- Atlassian's token semantics and accent governance
- Material's role-based typography and elevation logic
- Open MCT's mission-control clarity and composable dense layouts
- W3C/MDN accessibility requirements for contrast and motion

It should avoid:

- generic SaaS flatness
- theatrical sci-fi noise
- overloaded accent systems
- warm industrial or furnace-led metaphors

## Reference set

### Carbon Design System

Sources:

- [Color overview](https://carbondesignsystem.com/elements/color/overview/)
- [Motion overview](https://carbondesignsystem.com/elements/motion/overview/)
- [Data visualization color palettes](https://carbondesignsystem.com/data-visualization/color-palettes/)
- [Legends](https://carbondesignsystem.com/data-visualization/legends/)

What Carbon contributes:

- dark themes organized through layered neutrals
- a strong distinction between structure and sparse accent use
- role-based tokens rather than direct color-picking
- productive vs expressive motion
- a formal data-visualization palette and label/legend discipline

What to adopt:

- dark layers become lighter as elevation increases
- neutral grays do the heavy lifting
- primary action color is disciplined, not everywhere
- chart colors follow fixed categorical and sequential rules
- direct labels beat legends when space allows
- expressive motion is reserved for meaningful moments

What to avoid:

- Carbon's enterprise conservatism should not flatten Athanor into a sterile system
- Athanor can be more atmospheric than Carbon, but must keep Carbon's discipline

### Atlassian Design System

Sources:

- [Color foundation](https://atlassian.design/foundations/color)
- [Accents](https://atlassian.design/foundations/color-new/accents/)
- [Typography foundation](https://atlassian.design/foundations/typography/)
- [Design tokens explained](https://atlassian.design/foundations/tokens/design-tokens/)

What Atlassian contributes:

- clear separation of token meaning from raw value
- accent colors explicitly separated from semantic status colors
- structured typography roles
- elevation as a foundational UI concept

What to adopt:

- choose tokens by meaning, not by matching a hex
- accent colors should be swappable without changing semantic meaning
- status colors must remain semantically stable
- typography should be role-based and systemized

What to avoid:

- Atlassian's palette is product-general; Athanor needs a more cinematic and premium material identity than Atlassian's normal app surfaces

### Material / Android Design Guidance

Sources:

- [Material 3 in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3)
- [Wear dark theme guidance](https://developer.android.com/design/ui/wear/guides/m2-5/styles/color)
- [Material 3 expressive guidance](https://developer.android.com/design/ui/wear/guides/get-started/design-language)
- [Material theming codelab](https://developer.android.com/codelabs/m3-design-theming)

What Material contributes:

- role-based type scale
- shape/elevation logic
- explicit emphasis on readable type roles
- strong guidance around accessible contrast on dark themes
- warning about oversaturated colors on dark surfaces

What to adopt:

- a reduced but role-based type scale
- darker surfaces with carefully moderated saturation
- expressive display typography only where it improves hierarchy
- body and label roles optimized for dense reading

What to avoid:

- pure Material styling as the product identity
- overly rounded, consumer-soft visual language

### Open MCT / NASA mission-control references

Sources:

- [About Open MCT](https://nasa.github.io/openmct/about-open-mct)
- [Open MCT documentation](https://nasa.github.io/openmct/documentation/)
- [NASA Software Catalog entry](https://software.nasa.gov/software/ARC-15256-1D)

What Open MCT contributes:

- composable telemetry-rich views
- dense operational posture across desktop and mobile
- a mission-control tone grounded in real operational use
- flexible layouts that prioritize situational awareness over decorative novelty

What to adopt:

- operator-first clarity
- dense data presentation that still supports mobile
- mission-control restraint and composability

What to avoid:

- old-school aerospace visual nostalgia
- MCT-style utilitarian plainness without premium polish

### Accessibility and motion references

Sources:

- [W3C WCAG 2.2 contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [W3C WCAG 2.2 non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [USWDS theme color tokens](https://designsystem.digital.gov/design-tokens/color/theme-tokens/)

What these contribute:

- hard contrast floors
- focus/outline visibility requirements
- reduced-motion obligations
- tokenized, accessible color governance

What to adopt:

- accessible contrast requirements as design rules, not QA afterthoughts
- visible non-text contrast on inputs, outlines, borders, and focus indicators
- reduced-motion compatibility in the motion spec

## Adoption criteria

### Adopt

- layered neutrals
- semantic tokens
- strict status-vs-accent separation
- mission-control density
- role-based typography
- fixed chart grammar
- productive motion with limited expressive moments
- accessibility as a first-class design rule

### Avoid

- theme-by-aesthetic tinkering
- color chosen by intuition without role semantics
- decorative glow-heavy dark mode
- route-specific palette invention
- saturated color fields on dark backgrounds
- mixed metaphor systems

## What “futurist control room” means for Athanor

In Athanor terms, it means:

- dark, cool, layered surfaces
- readable telemetry and logs
- strong signal governance
- premium but disciplined materials
- sparse expressive moments around incidents, approvals, and system transitions

It does not mean:

- holographic clutter
- gratuitous neon
- decorative chrome
- retro terminal cosplay

## How far to push theatricality

Theatricality is acceptable only in:

- the command-center hero zone
- critical escalation moments
- launch-state transitions
- the visual brand signature of the shell

Theatricality is not acceptable in:

- dense tables
- charts
- long-lived operational cards
- notification surfaces
- repeated task lists

## Design thesis

The best Athanor look is:

`mission-control density + enterprise-grade token discipline + premium material depth + tightly governed multi-signal color`

That is the foundation for the token system and component standards that follow.
