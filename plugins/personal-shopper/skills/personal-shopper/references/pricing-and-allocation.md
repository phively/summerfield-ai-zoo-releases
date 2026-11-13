# Pricing and allocation method

Use this method for reproducible estimates. Show only the detail useful to the user.

## Price hierarchy

1. Current matching-location price at stores preferred for this product category in effective preference order, checking each supplied or saved preferred website before another suitable same-store source. For groceries, use the grocery-only order in [store preferences](store-preferences.md); do not apply it to other categories.
2. Current price at a comparable non-preferred retailer in the same region after preferred sources are insufficient
3. Recent regional price estimate
4. Broad estimate with low confidence

Treat sale, loyalty, coupon, delivery, and third-party marketplace prices as distinct. Prefer a normal non-member price unless the user confirms eligibility or asks for sale optimization.

For direct product comparisons, verify the same model, size, package, and included accessories where possible. Record the source and date checked, matching region, currency, exact model or package, offer conditions, and material exclusions such as tax, delivery, required accessories, or membership. Distinguish an observed matching-region price from a regional estimate or an offer whose eligibility is unconfirmed. Leave the price unknown when no reliable basis exists; do not imply that live research occurred when no source was checked.

For hardware, establish the exact matching variant and usable matching quantity before dividing pack price into unit price. Keep pack cost and cost per usable matching item separate, with compatible units and the conversion shown. A cheaper pack containing a different thread pitch, grade, length, material, or required coating is not an equivalent offer. Unknown pack counts or specifications leave unit cost or interchangeability unresolved; do not use a price comparison to override a fit requirement.

Use current-task instructions before applicable saved category preferences and explicitly general preferences. A one-time store order applies to the current task only; do not claim that it changed saved preferences without explicit consent and verified persistence.

## Service and project cost bases

Compare the same work, geography, timing, and deliverables. Break out materials, labor, disposal, travel, permit and inspection charges, taxes, and any risk provision when relevant. For each item, identify its source, date, currency, scope, amount or range, and whether it is included, excluded, estimated, conditional, or unknown. Provider advertising, a job-specific supplied quote, an official fee, and a modeled estimate are different evidence.

Show one-time charges separately from recurring fees, with billing period, minimum commitment, usage assumptions, and cancellation costs where applicable. Use a shared stated horizon for cumulative service costs; do not compare a monthly figure with an annual total as if their bases matched. For a conditional percentage fee, state the applicable base and tiers; missing balances or usage leave the total conditional.

Count each included charge once. If a quote or project base already includes materials, a permit allowance, tax, or contingency, show that inclusion rather than adding it again. If a final actual fee replaces an allowance, reconcile the difference explicitly. Unpriced exclusions remain unknown, and the known sum is a partial subtotal. Do not manufacture an all-in price or combine unsupported inputs into a precise total.

Use [project costs](project-costs.md) for official permit research and evidence-based reference-class forecasts; keep those calculations separate from grocery package and meal allocation.

## Core quantities

- **Required quantity:** total edible or recipe quantity after scaling and consolidation.
- **Purchase quantity:** whole packages needed after subtracting confirmed inventory and rounding up to available package sizes.
- **Checkout cost:** sum of full packages purchased for this shopping trip.
- **Allocated meal cost:** estimated value of the quantity consumed by a meal, including its share of common ingredients.
- **Pantry contribution:** replacement-value estimate for confirmed inventory consumed; exclude it from new checkout spending.

For a priced package:

`unit price = package price / usable package quantity`

`ingredient allocation to meal = unit price × quantity used by that meal`

Allocate an ingredient shared by several meals in proportion to each meal's required quantity. Charge the full package only once in checkout cost. Report likely surplus separately rather than assigning all surplus to the first meal.

## Practical rules

- Convert only compatible units. If density, trim loss, edible yield, or count-to-weight conversion is uncertain, use a range or leave the item unresolved.
- When the recipe requires part of an indivisible item, allocate the fraction consumed to meal cost while the checkout estimate includes the whole item or package.
- Include pantry ingredients in meal cost only when a reasonable replacement price is available; otherwise mark the meal estimate as partial.
- Do not silently choose premium, conventional, organic, generic, or specialty products. Follow the brief or state the assumed tier.
- Use exact displayed prices only for directly observed products. Round modeled totals sensibly and provide a range when several modeled inputs are uncertain.
- Never let an unpriced ingredient disappear from totals. List it as unknown and label affected meal totals as partial.

## Confidence

- **High:** current preferred-store and matching-location price with a matching package.
- **Medium:** current comparable local price or a close package conversion.
- **Low:** regional or broad estimate, uncertain conversion, or unclear product tier.

Overall confidence cannot exceed the confidence of a material share of the basket. Note which items drive the range.
