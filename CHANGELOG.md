# Changelog

## v0.1.0 — 2026-06-08

First public release.

### Added

- **Two nodes** — *Imagent: OpenAI Image* (text-to-image via `images.generate`) and
  *Imagent: OpenAI Image Edit* (edit / inpaint / multi-reference compose via `images.edit`).
- **Models** — `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1` (DALL·E excluded — shut down 2026-05-12).
- **Per-model dynamic UI** — the `model` widget swaps the size/background options per model and
  reveals only what each model supports: hi-res presets and custom `WxH` sizes for gpt-image-2,
  `transparent` background and `input_fidelity` for gpt-image-1.x. `custom_width` / `custom_height`
  appear only when `size = custom`.
- **Batch + multi-reference** — up to 8 images per call; the edit node takes an auto-growing set
  of up to 16 reference images plus an optional inpaint mask (white = region to edit).
- Quality, background, output format (`png` / `jpeg` / `webp`), output compression, and content
  moderation controls.
- **BYOK** — calls the OpenAI API directly with your own key (env `OPENAI_API_KEY` or a local
  `config.json`); no proxy, no per-image credit markup.

### Requirements

- ComfyUI ≥ 0.23.0 (the nodes use the `comfy_api` IO schema with `DynamicCombo`).
