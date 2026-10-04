# buy

`buy` is a Codex Agent Skill for researching grocery prices and building a source-linked comparison of ready-food and cook-at-home baskets from the same stores.

It supports:

- current product-price research with source URLs;
- package-level basket totals;
- ready price plus same-store cooking total in parentheses;
- optional, separately disclosed cashback;
- standalone responsive HTML output;
- syntax and structure validation.

## Install

```bash
git clone https://github.com/Solodovnick/skills.git ~/Solodovnick-skills
cp -R ~/Solodovnick-skills/skills/buy ~/.cursor/skills/buy
```

Invoke it explicitly as `$buy`.

## Validate a generated comparison

From the skill directory:

```bash
node scripts/validate-comparison.mjs /absolute/path/to/comparison.html
```

The skill is read-only with respect to real store carts and payments unless the user explicitly requests a separate transaction workflow.

## Example

[`examples/multistore-comparison.html`](examples/multistore-comparison.html) is a sanitized snapshot of a generated comparison. It demonstrates the layout and data wiring; its prices are not live offers.

Personal cashback details are deliberately excluded. To sanitize another generated page:

```bash
node scripts/sanitize-example.mjs input.html output.html
```
