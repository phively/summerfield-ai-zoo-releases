# Meal Planner

Install the Meal Planner plugin to plan household meals, select and adapt recipes, and coordinate grocery work for finalized meal plans.

## Skills

- `meal-planner:meal-planner` plans meals around household preferences and safety constraints.
- `meal-planner:personal-chef` selects and adapts recipes and maintains canonical recipe and preference records.

## Personal Shopper migration

Meal Planner 2.0 removed the bundled `meal-planner:personal-shopper` entry point. Install the independent Personal Shopper plugin and use `personal-shopper:personal-shopper` for direct product shopping and the full grocery workflow. Meal Planner delegates a finalized grocery packet to Personal Shopper only when the active host can activate that skill. When it is unavailable, Meal Planner uses only its documented bounded grocery fallback.

Installing or updating either plugin does not move, copy, rename, or delete shopping records. The existing canonical Grocery Preferences authority and native schema remain in place. No replacement workbook or parallel shopping record is created. Any requested owner-route change requires explicit authorization and verified readback of the existing destination and dependent routing metadata.
