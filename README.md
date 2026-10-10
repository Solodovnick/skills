# Skills

Reusable agent skills and workflows.

The canonical local checkout is `/Users/alex/github`, renamed from `gh` with Git history preserved. Shared skills are maintained here and registered as whole-directory symlinks under `~/.agents/skills/`. The older copies in `/Users/alex/ai/skills` are retained as references; update this checkout instead.

## Skills

- [`tts`](skills/tts/SKILL.md) — Russian PDF/Markdown-to-audiobook workflow with Qwen3-TTS 8-bit, batch-level pronunciation and word-form checks, independent Whisper QC, MP3 validation, and optional personal-library Yandex Music upload.
- [`music`](skills/music/SKILL.md) — Rights-aware publication of finished TTS audiobooks in Yandex Books and Yandex Music through an official publishing partner, including author registration, contracts, moderation, and release verification.
- [`meow`](skills/meow/SKILL.md) — Evidence-based Telegram meme analysis and a real-photo, anti-neuroslop workflow for writing, rendering, and visually validating community-native memes.
- [`buy`](skills/buy/SKILL.md) — Explicitly invoked grocery comparison with current prices, same-store baskets, and a verified HTML result.
- [`grill-me`](skills/grill-me/SKILL.md) — Explicit interview entry point; delegates to `grilling`.
- [`grilling`](skills/grilling/SKILL.md) — Rounds of dependent design decisions, with independent factual discovery before asking the user.

## Discovery and updates

Codex discovers these packages through `~/.agents/skills/<name>`, each pointing to `/Users/alex/github/skills/<name>`. Link the entire skill directory so scripts and references remain available. Preserve `buy` and `grill-me` as explicit-only skills through their `agents/openai.yaml` policies; other skills are selected when their task scope fits.

Read the selected `SKILL.md` before use. Resolve bundled scripts relative to that skill directory and use absolute paths for task inputs and outputs. On clients without a native Skill tool, `grill-me` works by loading its `grilling` dependency directly.

Imported source URLs, exact revisions, and file hashes are recorded in [`skills-lock.json`](skills-lock.json). Imported files stay at the pinned revision until a reviewed update; do not silently track an upstream branch. Keep client adapters separate when possible.

Workspace orchestration lives in `/Users/alex/AGENTS.md`, workshop routing in `/Users/alex/ai/AGENTS.md`, and Codex loading in `~/.codex/AGENTS.md`.

## GitHub delivery

This checkout publishes to `Solodovnick/skills`. Skill changes supplied under `/Users/alex/ai/skills` are reconciled here before committing; do not replace newer canonical instructions with older reference copies. After a requested skill change is verified, commit and push its reviewed files under the user's standing delivery instruction.

Other `/Users/alex/ai` project files belong in the separate private `Solodovnick/mac` repository. Keep private project data, credentials, model weights, environments, and caches out of this public skill library.
