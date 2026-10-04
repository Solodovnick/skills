# Grocery comparison data contract

Use one canonical store ID across every dataset.

```js
const stores = [
  {
    id: "store-id",
    name: "Store name",
    home: "https://store.example/",
    location: "City or store context",
    readyItems: [
      {
        category: "soup",
        name: "Prepared item",
        weight: "300 g",
        qty: 2,
        price: 199,
        url: "https://store.example/product"
      }
    ],
    cookItems: [
      {
        name: "Raw ingredient",
        weight: "1 kg",
        qty: 1,
        price: 89,
        url: "https://store.example/product"
      }
    ]
  }
];
```

## Calculations

```js
const lineTotal = item => item.price * (item.qty ?? 1);
const basketTotal = items => items.reduce((sum, item) => sum + lineTotal(item), 0);

const readyTotal = store => basketTotal(store.readyItems);
const cookTotal = store => basketTotal(store.cookItems);
```

Render the main price from these functions:

```html
<p class="store-price">
  READY_TOTAL ₽ <small class="cook-inline">(COOK_TOTAL ₽)</small>
</p>
<p>готовая корзина · в скобках — приготовить самому</p>
```

Never maintain a second hard-coded total in the HTML.

## Source metadata

For reproducibility, keep this metadata beside the dataset or in a checked-in JSON file:

```js
const snapshot = {
  observedAt: "YYYY-MM-DD",
  city: "City",
  deliveryIncluded: false,
  notes: ["Prices depend on address and availability"]
};
```

If a basket uses sources from different branches of the same chain, disclose that it is a catalog comparison rather than a guaranteed single-store checkout.

## Cashback metadata

```js
const cashback = {
  "store-id": {
    title: "Offer title",
    detail: "Channel, expiry, limit, and uncertainty",
    guaranteed: false
  }
};
```

Keep cashback out of the base basket total. Show any after-return scenario separately.

