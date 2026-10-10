# buy

`buy` is a Codex Agent Skill for researching grocery prices and building a source-linked comparison of ready-food and cook-at-home baskets from the same stores.

It supports:

- current product-price research with source URLs;
- package-level basket totals;
- ready price plus same-store cooking total in parentheses;
- optional, separately disclosed cashback;
- standalone responsive HTML output;
- syntax and structure validation.

## Local Codex registration

The canonical checkout is `/Users/alex/github`. Register the whole skill directory so references and scripts stay accessible:

```bash
mkdir -p ~/.agents/skills
ln -s /Users/alex/github/skills/buy ~/.agents/skills/buy
```

Create the link only if that destination is absent; preserve an existing correct link. See the [library index](../../README.md) for the shared setup.

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
