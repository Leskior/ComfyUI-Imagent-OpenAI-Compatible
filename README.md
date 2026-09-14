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
- 🚫 DALL·E intentionally excluded — all DALL·E models were shut down by OpenAI in 2026.

## 📦 Installation

> **Requires ComfyUI ≥ 0.23.0** — the nodes use the `comfy_api` IO schema (`DynamicCombo`) for the per-model UI.

### Option A — ComfyUI Manager (recommended)
Open **ComfyUI Manager → Custom Nodes Manager**, search for **`Imagent`**, click **Install**, and restart ComfyUI.

### Option B — git clone
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/agarzon/ComfyUI-Imagent.git
pip install -r ComfyUI-Imagent/requirements.txt
```
Restart ComfyUI.

## 🔑 API key

Imagent reads your key in this order:

1. **Environment variable** (preferred): set `OPENAI_API_KEY` before launching ComfyUI.
2. **`config.json`**: copy `config.example.json` → `config.json` (gitignored) in the extension directory and add your key.

> **Note:** OpenAI may require **API Organization Verification** before gpt-image models can be called. If your key is valid but you receive an authorization error, complete verification in the OpenAI dashboard — the error message logged to the ComfyUI console will tell you.

## 🧩 Nodes

### 🤖 Imagent: OpenAI Image

Text-to-image generation via `images.generate`.

| Parameter | Type | Values / Notes |
|---|---|---|
| `prompt` | STRING | Text description of the image to generate |
| `model` | **DynamicCombo** | `gpt-image-2.5-flare` (default), `gpt-image-2.5-sunburst`, `gpt-image-2`. Switching the model swaps the options below. |
| ↳ `size` | COMBO | `auto`, the three base sizes, five high-res presets, and `custom`. |
| ↳↳ `custom_width` / `custom_height` | INT | **Appear only when `size = custom`.** 1024–3840, step 16; both multiples of 16; aspect ≤ 3:1; total pixels 655,360–8,294,400. |
| ↳ `background` | COMBO | **gpt-image-2.5:** `auto`, `opaque`, `transparent` (needs `png`/`webp`). **gpt-image-2:** `auto`, `opaque`. |
| `quality` | COMBO | `auto`, `low`, `medium`, `high`, plus `xhigh` / `max` on gpt-image-2.5 (other models fall back to `high`). |
| `output_format` | COMBO | `png`, `jpeg`, `webp` |
| `output_compression` | INT | 0–100. Applied only for `jpeg` and `webp`. |
| `moderation` | COMBO | `auto` (default), `low`. Sent only when not `auto`. |
| `n` | INT | 1–8 images per call |

Rows marked ↳ live inside the dynamic `model` widget (appear only for models that support them); ↳↳ rows are nested one level deeper and appear only when their parent option is selected.

> No `seed` widget: OpenAI's image API has no seed, so it can't make outputs reproducible. ComfyUI's normal input-based caching applies — re-queuing an unchanged graph returns the cached image; change the prompt (or any input) to regenerate.

**Output:** `image` (IMAGE tensor, batch of n). Errors are logged to the ComfyUI console.

---

### 🤖 Imagent: OpenAI Image Edit

Image editing, inpainting, and multi-reference compositing via `images.edit`.

| Parameter | Type | Values / Notes |
|---|---|---|
| `prompt` | STRING | Description of the desired edit |
| `model` | **DynamicCombo** | Same three models; switching swaps the options below. |
| ↳ `size` | COMBO | Same as the generate node. |
| ↳↳ `custom_width` / `custom_height` | INT | **Appear only when `size = custom`.** Same rules as the generate node. |
| ↳ `background` | COMBO | gpt-image-2.5: `auto`/`opaque`/`transparent`; gpt-image-2: `auto`/`opaque`. |
| `images` | IMAGE (auto-grow) | Reference image(s) to edit — grows up to **16** slots; at least one required. |
| `quality` | COMBO | `auto`, `low`, `medium`, `high`, plus `xhigh` / `max` on gpt-image-2.5. |
| `output_format` | COMBO | `png`, `jpeg`, `webp` |
| `moderation` | COMBO | `auto` (default), `low` |
| `n` | INT | 1–8 images per call |
| `mask` *(optional)* | MASK | **White = region to edit.** Inpainting requires exactly one reference image. |

Rows marked ↳ live inside the dynamic `model` widget; ↳↳ rows appear only when their parent option is selected.

> No `input_fidelity` widget: every model shipped here always uses high input fidelity, and passing the parameter is an error. It only applied to the retired gpt-image-1.x models.

**Output:** `image` (IMAGE tensor, batch of n). Errors are logged to the ComfyUI console.

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
