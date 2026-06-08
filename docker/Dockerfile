# CPU-only image; Imagent calls the OpenAI API and does no local inference.
FROM python:3.11-slim

ARG COMFYUI_REF=master

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch ${COMFYUI_REF} \
        https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI

WORKDIR /opt/ComfyUI
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# Imagent's only runtime dep beyond ComfyUI (Pillow/numpy/torch ship with ComfyUI).
RUN pip install "openai>=1.40.0"

EXPOSE 8188
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--cpu"]
