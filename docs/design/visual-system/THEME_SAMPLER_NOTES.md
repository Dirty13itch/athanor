# Theme Sampler Notes

This file accompanies the command-center theme sampler. The canonical operator URL is `https://athanor.local/`; if the current client still lacks hostname rollout for that alias, use the temporary DEV runtime fallback at [http://dev.athanor.local:3001/catalog](http://dev.athanor.local:3001/catalog).

## Purpose

The first sampler pass was rejected correctly because the options were too close together. This second pass uses **distinct dark-system families** that are already respected for readability, dark-mode discipline, or semantic color design.

The sampler keeps the same miniature Command Center layout across all options so the comparison stays visual, not structural.

## Theme Families

### Pure Monochrome OLED
- Direction: near-black background, white and gray stack, one bright control accent.
- Best for: severe clarity, minimal noise, strong operator focus.
- Risk: can feel too stark if you want more atmosphere.

### GitHub Dark Dimmed
- Direction: softened slate dark with restrained accents and long-session ergonomics.
- Best for: mature, low-fatigue product polish.
- Risk: may feel too restrained if you want stronger personality.

### GitHub Dark High Contrast
- Direction: sharper black/slate contrast and more decisive boundaries.
- Best for: operator speed, scannability, and strong separation.
- Risk: can feel less luxurious than more atmospheric options.

### Carbon Ops
- Direction: charcoal, dense enterprise instrumentation, disciplined IBM-style blue.
- Best for: industrial operations-platform credibility.
- Risk: can feel institutional if pushed too hard.

### GitLab Dark Restraint
- Direction: reduced-color dark UI with a slightly plum shell and carefully controlled accents.
- Best for: a balanced dark enterprise feel with more character than Carbon.
- Risk: easiest option to drift toward “product dark” instead of “control room” if not tuned.

### Nord Arctic
- Direction: cool blue-gray neutrals with calm frost accents.
- Best for: elegant and technical without being harsh.
- Risk: can become too soft if operator urgency needs to dominate.

### Catppuccin Mocha
- Direction: richer pastel-driven dark theme with softened edges and more emotional color.
- Best for: a premium, distinctive, more expressive control surface.
- Risk: easiest to feel less operational if signal governance slips.

### Material 3 Expressive Dark
- Direction: richer semantic surface roles and more dynamic accent interplay.
- Best for: route/domain flexibility and stronger semantic color behavior.
- Risk: can feel app-system generic unless kept very disciplined.

## Current Recommendation

Based on the stated preference for blacks, whites, grays, and bright accents, the strongest candidates are:

1. `Pure Monochrome OLED`
2. `GitHub Dark High Contrast`
3. `GitHub Dark Dimmed`
4. `Nord Arctic`

If the goal is a slightly more premium or styled version after that shortlist, the next two worth testing are:

5. `Carbon Ops`
6. `Catppuccin Mocha`

## Research Anchors

These were chosen from well-regarded dark-system references, not invented in isolation:

- [GitHub theme settings](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-user-account/managing-user-account-settings/managing-your-theme-settings)
- [Primer color usage](https://primer.style/product/getting-started/foundations/color-usage/)
- [IBM Carbon color overview](https://carbondesignsystem.com/elements/color/overview/)
- [IBM Carbon color usage](https://carbondesignsystem.com/elements/color/usage/)
- [GitLab Pajamas color foundations](https://design.gitlab.com/product-foundations/color/)
- [GitLab dark mode update](https://about.gitlab.com/blog/gitlab-dark-mode-is-getting-a-new-look/)
- [Nord color palettes](https://www.nordtheme.com/docs/colors-and-palettes)
- [Catppuccin palette](https://catppuccin.com/palette)
- [Material 3 overview](https://m3.material.io/)
- [Material 3 design tokens in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3)

## What To Watch For

When reviewing the sampler, the most important question is not “which looks coolest?” It is:

- which one makes posture easiest to read
- which one makes alerts and approvals clearest
- which one makes agent/task state easiest to scan
- which one still feels good after staring at it for a long session
- which one looks like Athanor should look, not just a nice generic dark dashboard
