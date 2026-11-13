# Personal Shopper

Install Personal Shopper 1.1 to compare products, services, contractors, and project costs, or complete priced grocery work from Meal Planner's approved `grocery-handoff/v1` packet. Its entry point is `personal-shopper:personal-shopper`.

## Moving from Meal Planner

Meal Planner 2.0 removed the bundled `meal-planner:personal-shopper` entry point. Install Personal Shopper separately and use `personal-shopper:personal-shopper` for direct product research, price comparisons, and shopping-record maintenance. For grocery consolidation from finalized recipes, Meal Planner sends its approved `grocery-handoff/v1` packet when the active host can activate Personal Shopper. A direct product-shopping request does not require recipes or Meal Planner.

Changing the skill entry point does not move, copy, rename, or delete shopping records. Continue with the user's existing canonical shopping authority and native schema. Installing this plugin does not create a replacement workbook or migrate personal data. Update an external owner route only when the user authorizes that change, and verify the existing destination and dependent routing metadata before reporting it complete.

If Personal Shopper cannot be activated or its established record authority is unavailable, report the limitation and any proposed update as pending. Do not create a parallel shopping record or claim that personal records migrated.

## Direct research

Name the need, hard requirements, priorities, and relevant location. The shopper researches alternatives to a named product or service unless you restrict the comparison. Hardware research retrieves applicable specifications for the exact variant and compares prices per usable matching item. Service comparisons distinguish scope, qualifications, deliverables, timing, exclusions, and one-time or recurring fees.

For projects, the shopper researches applicable official permit rules and fees, separates quotes and estimates from unknown costs, and avoids counting included allowances twice. A reference-class forecast requires comparable completed outcomes, a matching estimate basis, and a stated calculation method. When that evidence is inadequate, the result explains the gap and provides any supportable ordinary estimate.

Research uses the host's available tools without requiring another research plugin. Unavailable specifications, qualifications, fees, and forecast inputs remain explicit. A recommendation does not authorize contacting providers, requesting quotes, booking, applying, purchasing, paying, or saving records. Confirmed task preferences stay task-only unless you authorize a durable update to the existing scoped authority. The approved meal-plan grocery contract and Meal Planner fallback remain unchanged.
