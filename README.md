<p align="center">
  <img src="assets/banner.png" alt="ComfyUI-Imagent — OpenAI image generation and editing for ComfyUI" width="100%">
</p>

<h1 align="center">ComfyUI-Imagent</h1>

<p align="center">
  <strong>BYOK OpenAI image generation and editing nodes for ComfyUI.</strong><br>
  Bring your own OpenAI API key — calls go directly to OpenAI, no proxy, no extra credits.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <a href="https://wallrus.tech"><img alt="Sponsored by Wallrus" src="https://img.shields.io/badge/sponsored%20by-Wallrus-7c3aed"></a>
</p>

---

## ✨ Features

- 🖼️ **Two nodes** — **Imagent: OpenAI Image** (text-to-image) and **Imagent: OpenAI Image Edit** (edit, inpaint, multi-reference compose).
- 🤖 **Current gpt-image models** — `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, `gpt-image-2`.
- ✍️ **Text-to-image** with full control over size, quality, background, and output format.
- 🎨 **Edit + inpaint (mask)** — supply a mask to repaint a specific region; white pixels mark the area to edit.
- 🔗 **Multi-reference compositing** — feed up to 16 reference images to the edit node (auto-growing input).
- 🎛️ **Per-model UI** — the `model` widget is dynamic: switching models swaps the size list and shows only the options that model supports (no invalid combos).
- 🏞️ **Up to 8 images per call** — batch generation in a single node execution.
- 🛡️ **Optional content moderation** — `auto` (default) or `low`.
- 🔑 **BYOK — your own OpenAI API key, your own costs.** Unlike ComfyUI's built-in OpenAI nodes (which route through ComfyUI's paid proxy), Imagent calls the OpenAI API directly. No proxy, no per-image credit markup.
- 🔌 **OpenAI-compatible endpoints** — set `OPENAI_BASE_URL` (env, `config.json`, or the node's `base_url` input) and pick `custom` as the model to send any other endpoint's model id.
- 🚫 DALL·E intentionally excluded — all DALL·E models were shut down by OpenAI in 2026.

## 📦 Installation

> **Requires ComfyUI ≥ 0.23.0** — the nodes use the `comfy_api` IO schema (`DynamicCombo`) for the per-model UI.

This fork adds OpenAI-compatible endpoint support to
[ComfyUI-Imagent](https://github.com/agarzon/ComfyUI-Imagent) and is not on the ComfyUI
Registry, so install it from source:

### Option A — git clone (recommended)
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Leskior/ComfyUI-Imagent-OpenAI-Compatible.git
pip install -r ComfyUI-Imagent-OpenAI-Compatible/requirements.txt
```
Restart ComfyUI.

### Option B — link an existing checkout
Keeping the checkout outside `custom_nodes` and linking it in makes editing it easier. On Windows:

```powershell
New-Item -ItemType Junction -Path "C:\path\to\ComfyUI\custom_nodes\comfyui-imagent" -Target "C:\path\to\your\checkout"
```
Restart ComfyUI.

> Upstream's node is on **ComfyUI Manager** (search `Imagent`), but that installs the version
> *without* the OpenAI-compatible endpoint support. Don't install both — they register the same
> node ids.

## 🔑 API key & endpoint

Imagent resolves both settings from the environment first, then `config.json`, and each node can override them per call:

| Setting | Environment variable | `config.json` key |
|---|---|---|
| API key | `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| Base URL | `OPENAI_BASE_URL` | `OPENAI_BASE_URL` |

1. **Environment variables** (preferred): set `OPENAI_API_KEY` — and `OPENAI_BASE_URL` when you are not calling OpenAI — before launching ComfyUI.
2. **`config.json`**: copy `config.example.json` → `config.json` (gitignored) in the extension directory and fill in your values.
3. **`api_key` / `base_url` node inputs**: blank by default; when filled they win over the two sources above. Prefer 1 and 2 — a key typed into a widget is saved in the workflow file, so it travels with any workflow you share.

`OPENAI_BASE_URL` includes the version segment, e.g. `https://your-gateway.example/v1`. Leave it blank to use `https://api.openai.com/v1`.

> **Note:** OpenAI may require **API Organization Verification** before gpt-image models can be called. If your key is valid but you receive an authorization error, complete verification in the OpenAI dashboard — the error message logged to the ComfyUI console will tell you.

## 🔌 OpenAI-compatible endpoints

The nodes speak the OpenAI Images API, so a self-hosted gateway or a third-party provider that implements it works too — set the base URL and send that endpoint's own model id by picking `custom` in the `model` dropdown and filling in `model_name`.

Selecting `custom` turns off the per-model gating described in the tables below: the endpoint's capabilities are unknown, so `quality` and `background` are sent exactly as configured and whatever the endpoint does not support comes back as its own error.

> **Known limit:** `size` still offers only the gpt-image presets, and a custom `WxH` must satisfy the gpt-image rules (both edges 480–3840 and multiples of 16, aspect ≤ 3:1, total pixels 655,360–8,294,400). Sizes outside that — `512x512`, for example — cannot be entered in the UI; use `auto` if the endpoint accepts it.

## 🧩 Nodes

### 🤖 Imagent: OpenAI Image

Text-to-image generation via `images.generate`.

| Parameter | Type | Values / Notes |
|---|---|---|
| `prompt` | STRING | Text description of the image to generate |
| `model` | **DynamicCombo** | `gpt-image-2.5-flare` (default), `gpt-image-2.5-sunburst`, `gpt-image-2`, or `custom`. Switching the model swaps the options below. |
| ↳ `model_name` | STRING | **`custom` only.** Model id sent to the endpoint, e.g. `flux-1.1-pro`. Required when `model = custom`. |
| ↳ `size` | COMBO | `auto`, the three base sizes, five high-res presets, and `custom`. |
| ↳↳ `custom_width` / `custom_height` | INT | **Appear only when `size = custom`.** 480–3840, step 16; both multiples of 16; aspect ≤ 3:1; total pixels 655,360–8,294,400. |
| ↳ `background` | COMBO | **gpt-image-2.5:** `auto`, `opaque`, `transparent` (needs `png`/`webp`). **gpt-image-2:** `auto`, `opaque`. **`custom`:** all three, passed through unchanged. |
| `quality` | COMBO | `auto`, `low`, `medium`, `high`, plus `xhigh` / `max` on gpt-image-2.5 (other models fall back to `high`; `custom` passes the value through). |
| `output_format` | COMBO | `png`, `jpeg`, `webp` |
| `output_compression` | INT | 0–100. Applied only for `jpeg` and `webp`. |
| `moderation` | COMBO | `auto` (default), `low`. Sent only when not `auto`. |
| `n` | INT | 1–8 images per call |
| `base_url` | STRING | Optional per-node override of `OPENAI_BASE_URL` / `config.json`. Blank falls back to the env var, then `config.json`, then `https://api.openai.com/v1`. |
| `api_key` | STRING | Optional per-node override of `OPENAI_API_KEY` / `config.json`. Blank falls back to the env var, then `config.json`. |

Rows marked ↳ live inside the dynamic `model` widget (appear only for models that support them); ↳↳ rows are nested one level deeper and appear only when their parent option is selected.

> No `seed` widget: OpenAI's image API has no seed, so it can't make outputs reproducible. ComfyUI's normal input-based caching applies — re-queuing an unchanged graph returns the cached image; change the prompt (or any input) to regenerate.

**Outputs:** `image` (IMAGE tensor, batch of n) and `mask` (MASK tensor). Errors are logged to the ComfyUI console.

ComfyUI's IMAGE type is RGB, so when `background = transparent` the alpha channel comes out on
`mask` instead — following the `LoadImage` convention, `mask = 1 - alpha`, meaning a transparent
region reads as selected (1.0). The `image` preview will look black in those regions; that is the
alpha being discarded for display, not a failed generation. To get a transparent file, feed
`image` and `mask` into **Join Image with Alpha** (it inverts the mask internally, so no
`InvertMask` in between) and save the result. Opaque output gives an all-zero mask.

---

### 🤖 Imagent: OpenAI Image Edit

Image editing, inpainting, and multi-reference compositing via `images.edit`.

| Parameter | Type | Values / Notes |
|---|---|---|
| `prompt` | STRING | Description of the desired edit |
| `model` | **DynamicCombo** | Same models as the generate node, including `custom`; switching swaps the options below. |
| ↳ `model_name` | STRING | **`custom` only.** Model id sent to the endpoint. Required when `model = custom`. |
| ↳ `size` | COMBO | Same as the generate node. |
| ↳↳ `custom_width` / `custom_height` | INT | **Appear only when `size = custom`.** Same rules as the generate node. |
| ↳ `background` | COMBO | gpt-image-2.5: `auto`/`opaque`/`transparent`; gpt-image-2: `auto`/`opaque`; `custom`: all three, passed through unchanged. |
| `images` | IMAGE (auto-grow) | Reference image(s) to edit — grows up to **16** slots; at least one required. |
| `quality` | COMBO | `auto`, `low`, `medium`, `high`, plus `xhigh` / `max` on gpt-image-2.5 (`custom` passes the value through). |
| `output_format` | COMBO | `png`, `jpeg`, `webp` |
| `moderation` | COMBO | `auto` (default), `low` |
| `n` | INT | 1–8 images per call |
| `mask` *(optional)* | MASK | **White = region to edit.** Inpainting requires exactly one reference image. |
| `base_url` | STRING | Optional per-node override of `OPENAI_BASE_URL` / `config.json`. |
| `api_key` | STRING | Optional per-node override of `OPENAI_API_KEY` / `config.json`. |

Rows marked ↳ live inside the dynamic `model` widget; ↳↳ rows appear only when their parent option is selected.

> No `input_fidelity` widget: every model shipped here always uses high input fidelity, and passing the parameter is an error. It only applied to the retired gpt-image-1.x models.

**Outputs:** `image` (IMAGE tensor, batch of n) and `mask` (MASK tensor). Errors are logged to the ComfyUI console.

ComfyUI's IMAGE type is RGB, so when `background = transparent` the alpha channel comes out on
`mask` instead — following the `LoadImage` convention, `mask = 1 - alpha`, meaning a transparent
region reads as selected (1.0). The `image` preview will look black in those regions; that is the
alpha being discarded for display, not a failed generation. To get a transparent file, feed
`image` and `mask` into **Join Image with Alpha** (it inverts the mask internally, so no
`InvertMask` in between) and save the result. Opaque output gives an all-zero mask.

**Quick-start recipes:**
- **Edit:** connect one image to `images`, write a `prompt`, leave `mask` disconnected.
- **Inpaint:** connect one image + `mask` (white = area to repaint), write a `prompt`.
- **Multi-reference:** connect several images (the input grows as you wire them up), write a `prompt`. Mask not supported for multi-image calls.

## 🛠️ Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest -q
```

### Smoke testing with Docker
Set your API key first — either export `OPENAI_API_KEY` in your shell, or copy `config.example.json` → `config.json` and add your key. Then:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

ComfyUI will be available at **http://localhost:8188** with Imagent pre-loaded. For Python changes, restart the container. The repo is bind-mounted into the container's `custom_nodes/` directory.

## 🐾 The story behind the name

**Imagent** = **image** + **agent**. A small model-driven agent that images things into existence — and edits them once they're there.

It comes from **Wallrus**, whose own name blends a *social **wall*** with a ***walrus***. Two friendly ideas, one tool: straightforward, reliable image generation without the middleman.

## 💙 Sponsored by Wallrus

ComfyUI-Imagent is proudly sponsored by **[Wallrus](https://wallrus.tech)**. If Imagent makes your ComfyUI workflow nicer, go say hi. 👋

## 📄 License

[MIT](LICENSE) © 2026 Alexander Garzon
