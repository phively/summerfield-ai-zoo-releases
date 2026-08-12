# Pricing and allocation method

Use this method for reproducible estimates. Show only the detail useful to the user.

## Price hierarchy

1. Current matching-location price at preferred stores in effective preference order, checking each supplied or saved preferred website before another suitable same-store source
2. Current price at a comparable non-preferred retailer in the same region after preferred sources are insufficient
3. Recent regional price estimate
4. Broad estimate with low confidence

Treat sale, loyalty, coupon, delivery, and third-party marketplace prices as distinct. Prefer a normal non-member price unless the user confirms eligibility or asks for sale optimization.

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
