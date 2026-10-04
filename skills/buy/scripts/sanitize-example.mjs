#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const [input, output] = process.argv.slice(2);

if (!input || !output) {
  console.error("Usage: node scripts/sanitize-example.mjs <input.html> <output.html>");
  process.exit(2);
}

const source = path.resolve(input);
const target = path.resolve(output);

if (!fs.existsSync(source)) {
  console.error(`Missing file: ${source}`);
  process.exit(2);
}

let html = fs.readFileSync(source, "utf8");

const genericCashbackData = `    const CASHBACK = {
      magnit: { title: "Проверьте кэшбэк для Магнита", detail: "персональные условия не включены в публичный пример" },
      pyaterochka: { title: "Проверьте кэшбэк для Пятёрочки", detail: "персональные условия не включены в публичный пример" },
      vkusvill: { title: "Проверьте кэшбэк для ВкусВилла", detail: "персональные условия не включены в публичный пример" },
      ozon: { title: "Проверьте кэшбэк для Ozon Fresh", detail: "персональные условия не включены в публичный пример" },
      lavka: { title: "Проверьте кэшбэк для Яндекс Лавки", detail: "персональные условия не включены в публичный пример" }
    };`;

html = html.replace(
  /    const CASHBACK = \{[\s\S]*?\n    \};\n\n    const COOK_STORES/,
  `${genericCashbackData}\n\n    const COOK_STORES`
);

const genericCashbackSection = `    <section class="section" id="cashback">
      <div class="section-head">
        <div>
          <p class="eyebrow" style="color: var(--green)">Не входит в пример</p>
          <h2>Персональный кэшбэк</h2>
          <p class="section-lead">Проверьте доступные предложения в своём банке перед оплатой. Персональные ставки, сроки и лимиты намеренно не сохранены в этом примере.</p>
        </div>
      </div>
      <div class="fine-print">
        <span aria-hidden="true">ⓘ</span>
        <div><strong>Важно:</strong> кэшбэк не уменьшает цену на кассе и не включён в рейтинг корзин. Добавляйте его только после проверки условий для конкретного магазина и канала покупки.</div>
      </div>
    </section>

    <section class="section" id="method">`;

html = html.replace(
  /    <section class="section" id="cashback">[\s\S]*?    <section class="section" id="method">/,
  genericCashbackSection
);

html = html
  .replace("снимок каталога и личной витрины", "снимок каталогов")
  .replace("Сопоставили видимые предложения из вашего кабинета с магазинами выше. ", "");

fs.mkdirSync(path.dirname(target), { recursive: true });
fs.writeFileSync(target, html);
console.log(`Sanitized example written to ${target}`);

