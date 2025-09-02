# Eval of DOTS OCR Engine Using Baseten

A document intelligence and extraction engine using [DOTS OCR](https://huggingface.co/rednote-hilab/dots.ocr) model deployed with Truss on [Baseten](https://baseten.com).

To deploy dots.ocr on Baseten follow this [Repo](https://github.com/tobalo/dots.ocr.truss.git)

## Quick Start
```bash
cp .env.example .env # Ensure the MODEL_API_URL is mapped to your Baseten Model URL from above
uv sync
uv run -m evals
```
