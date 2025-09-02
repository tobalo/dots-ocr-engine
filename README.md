# DOTS OCR Engine Using Baseten

A document intelligence and extraction engine using [DOTS OCR](https://huggingface.co/rednote-hilab/dots.ocr) model deployed with Truss on [Baseten](https://baseten.com).

TODO:
- Stabilize Truss push of dots.ocr

## WIP: Working through stable push to Baseten

### 0. Setup environment variable
Create your `.env` file with the following command:
```bash
cp .env.example .env
```

Provision the respective API keys from the respective service.

### 1. Install Truss to publish

```bash
uv venv
source .venv/bin/active # If you're trying this on windows Godspeed
uv pip install truss
cd ..
truss push dots-ocr-engine --publish
```
You are now publishing the `config.yaml` to Baseten to run your model inference API.

### 2. Load your samples
```bash
mkdir samples
mkdir sample_outputs
```

### 3. Run Evaluation
```bash
uv sync
uv run -m evals
```