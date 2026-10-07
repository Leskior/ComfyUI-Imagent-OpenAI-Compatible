# Changelog

## v0.3.0 — 2026-10-08

### Added

- **OpenAI-compatible endpoints** — the base URL now comes from `OPENAI_BASE_URL`
  (environment) or `config.json`, and both nodes gained an optional `base_url`
  input that overrides both. Point it at any gateway or provider that speaks the
  OpenAI Images API, e.g. `https://your-gateway.example/v1`; blank keeps
  `https://api.openai.com/v1`. Both nodes also gained an optional `api_key` input
  that overrides `OPENAI_API_KEY` / `config.json` for that node.
  **Both nodes gained two inputs, so saved workflows will show the node as changed.**
- **`custom` model selection** — the `model` dropdown's new `custom` option reveals
  a `model_name` field for an arbitrary model id (e.g. `flux-1.1-pro`), because
  compatible endpoints rarely serve the `gpt-image-*` ids. A custom model skips the
  capability gating: `quality` and `background` are sent exactly as configured and
  the endpoint reports whatever it does not support. `size` keeps the gpt-image
  preset list and `WxH` rules.
- `OPENAI_BASE_URL` is forwarded by the Docker smoke-test compose file.

## v0.2.0 — 2026-09-14

### Added

- **gpt-image-2.5** — `gpt-image-2.5-flare` (new default) and `gpt-image-2.5-sunburst`, with
  custom `WxH` sizes, `transparent` background, and the new `xhigh` / `max` quality tiers.
  gpt-image-2 falls back to `high` when an extended tier is selected.
- **`mask` output on both nodes** — ComfyUI IMAGE is RGB, so a `transparent` background used to
  be flattened onto black and lost. Alpha now comes out as a MASK (`1 - alpha`, matching
  `LoadImage`); pair it with **Join Image with Alpha** to save a transparent PNG. Opaque output
  yields an all-zero mask. **Both nodes gained a second output, so saved workflows will show the
  node as changed.**

### Fixed

- **`custom_width` / `custom_height` minimum lowered from 1024 to 480** — the widget floor was
  stricter than `validate_custom_dimensions()`, so legal sizes such as `1536x864` and `1440x480`
  could not be entered and silently snapped up to 1024.

### Removed

- **gpt-image-1 and gpt-image-1.5** — OpenAI shuts them down on 2026-10-23 and 2026-12-01
  respectively. **Saved workflows that select either model will need their `model` widget
  re-picked.**
- **`input_fidelity`** — it only ever applied to gpt-image-1.x; gpt-image-2 and 2.5 always use
  high input fidelity and error if the parameter is sent. The widget is gone from the edit node
  and the parameter is no longer part of `build.run_edit()`.

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
