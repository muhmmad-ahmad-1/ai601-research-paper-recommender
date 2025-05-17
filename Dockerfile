FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY src/ ./src/

ENV HF_HOME=/app/.cache/huggingface

RUN mkdir -p /app/.cache/huggingface

RUN pip3 install -r requirements.txt
RUN pip3 install grpcio==1.71.0 --force-reinstall

RUN pip install huggingface-hub

# Clear the Huggingface cache
RUN rm -rf ~/.cache/huggingface

# Step 1: Patch config and save local path
RUN echo "\
from huggingface_hub import snapshot_download\n\
import os, json\n\
path = snapshot_download('thenlper/gte-large')\n\
cfg_path = os.path.join(path, 'config.json')\n\
with open(cfg_path, 'r+', encoding='utf-8') as f:\n\
    config = json.load(f)\n\
    if 'model_type' not in config:\n\
        config['model_type'] = 'bert'\n\
        f.seek(0)\n\
        json.dump(config, f)\n\
        f.truncate()\n\
with open('/tmp/model_path.txt', 'w') as f:\n\
    f.write(path)\n\
" > /tmp/patch_and_save.py && python3 /tmp/patch_and_save.py

        
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('thenlper/gte-large')"


EXPOSE 7860

HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

ENTRYPOINT ["streamlit", "run", "src/frontend/app.py", "--server.port=7860", "--server.address=0.0.0.0"]