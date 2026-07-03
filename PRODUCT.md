# PRODUCT.md — Pro Tools Session Builder

## Register
Product. Design serves the task: a desktop utility used mid-workflow, next to Pro Tools.

## Users & Purpose
One user (an audio engineer/musician) batch-preparing Pro Tools sessions from song
folders: scan audio, detect specs, queue jobs, let the tool drive Pro Tools via PTSL.
Used at a mixing desk, room lights low, Pro Tools (a dark UI) on the same screen.
The tool should disappear into the task and read instantly at a glance:
what's queued, what's running, what failed, why.

## Personality
Studio utility — quiet, dense, engineered, like a well-built rack unit.
Neutral dark grays, a single restrained accent for actions/selection/progress,
no decoration. Status must be readable from across the room.

## Anti-references
- Consumer-app playfulness, gradients, glassmorphism, big rounded cards
- SaaS dashboard hero metrics
- Anything that visually competes with Pro Tools for attention

## Design principles
1. Dark theme, matching the studio and the DAW (Fusion base + app QSS).
2. Restrained color: one accent for primary action/selection/progress;
   semantic colors reserved for job status (running/completed/failed).
3. Density over whitespace; tables and logs carry real information.
4. Every control state defined: default, hover, focus, pressed, disabled.
5. Standard macOS affordances: native menu bar, native dialogs, no invented controls.

## Accessibility
Body text ≥ 4.5:1 against surfaces; status conveyed by label text as well as color.
Keyboard: standard focus order, visible focus rings on inputs.
