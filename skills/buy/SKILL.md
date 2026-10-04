---
name: buy
description: Builds and updates grocery shopping comparisons with same-store ready-food and cook-at-home baskets, current product prices, optional cashback, and a verified standalone HTML site. Use when the user invokes $buy to compare grocery stores, assemble food baskets, contrast prepared meals with ingredients, or update a grocery comparison page.
disable-model-invocation: true
---

# Buy

Build a source-linked grocery comparison without placing an order.

## Inputs

Infer these from the conversation when they are already known. Ask only when a missing choice would materially change the result.

- Delivery city or store location.
- Stores to compare.
- Number of people or portions.
- Ready-food scenario and cook-at-home scenario.
- Existing site path, if this is an update.
- Whether personal cashback should be included.

## Workflow

1. Inspect the existing site, its data structures, and the closest project instructions.
2. Define the two baskets before researching prices:
   - `ready`: prepared dishes that can be eaten or reheated;
   - `cook`: raw ingredients or staples that require cooking.
3. Keep both baskets mapped by the same stable store ID.
4. Research current prices and retain a source URL for every line item.
5. Calculate totals from line items. Never hand-type a displayed total separately from its data.
6. Update the site with the smallest cohesive change.
7. Run `node scripts/validate-comparison.mjs <html-path>`.
8. Render the affected section at desktop and mobile widths and inspect the screenshots.
9. Report the result, caveats, validation, and file or publication link.

## Price research rules

- Prices are time-sensitive: browse on every fresh comparison.
- Prefer official product pages or the store's rendered catalog.
- Record the observation date, location context, package weight, price, and URL.
- If an official price is unavailable, label any public catalog mirror or search result honestly.
- Compare the amount actually paid for available packages. Do not silently prorate a large pack to the recipe amount.
- Explain meaningful leftovers, minimum-order constraints, delivery fees, or address-dependent availability.
- Do not invent a product, price, discount, or cashback condition.

## Comparison integrity

- A cook-at-home total must come from products sold by the same store as the ready-food total beside it.
- If the two baskets represent different meals, say so explicitly. Do not present them as equivalent savings.
- When the user requests one number in parentheses, render `READY_TOTAL (COOK_TOTAL)` and explain directly below that the parenthetical value is the cook-at-home basket.
- Preserve full ingredient details in a dedicated cooking section even when the card shows only its total.
- Sort and rank ready baskets independently from cooking baskets unless the user requests another method.

See [references/data-contract.md](references/data-contract.md) for the recommended data model.

## Cashback

- Treat cashback as personal, conditional, and separate from shelf price.
- Use it only from information the user supplied or an authenticated view they explicitly placed in scope.
- Record channel, limit, expiry, minimum spend, and uncertainty.
- Do not activate an offer, change a cart, place an order, or pay unless the user explicitly asks for that action.
- Never present an upper-bound “up to” rate as guaranteed savings.

## Site requirements

- Prefer a portable standalone HTML file when the existing project uses that format.
- Use [examples/multistore-comparison.html](examples/multistore-comparison.html) as a structural reference, not as a current price source.
- Keep store and basket data centralized in JavaScript objects.
- Generate cards, totals, ranking bars, and copyable lists from data.
- Give every external link `target="_blank"` and `rel="noopener noreferrer"`.
- Clearly state the price date, location limitations, delivery exclusions, and meaning of parentheses.
- Preserve existing visual language and responsive breakpoints.
- Do not publish personal screenshots, account identifiers, authentication data, or raw banking exports.

To create a shareable example from a personalized local page, run `node scripts/sanitize-example.mjs <input.html> <output.html>` before publishing it.

## Validation

Run:

```bash
node scripts/validate-comparison.mjs path/to/comparison.html
```

The check must pass before handoff. Also verify in a browser that:

- every store has both totals;
- the parenthetical value belongs to the same store;
- currency formatting and wrapping remain legible;
- desktop and mobile layouts do not overlap;
- product and store links are clickable;
- no real cart or account state changed during read-only research.
