#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const input = process.argv[2];

if (!input) {
  console.error("Usage: node scripts/validate-comparison.mjs <html-path>");
  process.exit(2);
}

const file = path.resolve(input);
if (!fs.existsSync(file)) {
  console.error(`Missing file: ${file}`);
  process.exit(2);
}

const html = fs.readFileSync(file, "utf8");
const errors = [];

if (!/^<!doctype html>/i.test(html.trimStart())) {
  errors.push("missing HTML doctype");
}

const ids = [...html.matchAll(/\bid=["']([^"']+)["']/gi)].map(match => match[1]);
const duplicates = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
if (duplicates.length) {
  errors.push(`duplicate IDs: ${duplicates.join(", ")}`);
}

for (const id of ["comparison", "offers", "cook"]) {
  if (!ids.includes(id)) errors.push(`missing #${id} section`);
}

const inlineScripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)];
if (!inlineScripts.length) {
  errors.push("missing inline JavaScript");
} else {
  inlineScripts.forEach((match, index) => {
    try {
      new Function(match[1]);
    } catch (error) {
      errors.push(`inline script ${index + 1} does not compile: ${error.message}`);
    }
  });
}

for (const marker of ["cook-inline", "COOK_STORES", "cookTotal"]) {
  if (!html.includes(marker)) errors.push(`missing ready/cook mapping marker: ${marker}`);
}

const blankLinks = [...html.matchAll(/<a\b[^>]*target=["']_blank["'][^>]*>/gi)];
for (const match of blankLinks) {
  if (!/\brel=["'][^"']*noopener[^"']*noreferrer[^"']*["']/i.test(match[0])) {
    errors.push(`unsafe external link: ${match[0].slice(0, 120)}`);
  }
}

if (errors.length) {
  console.error("Validation failed:");
  errors.forEach(error => console.error(`- ${error}`));
  process.exit(1);
}

console.log(`OK: ${file}`);
console.log(`- ${ids.length} unique IDs`);
console.log(`- ${inlineScripts.length} inline script block(s) compile`);
console.log(`- ready/cook comparison markers found`);

