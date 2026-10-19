# ultimatetruth.one

One question about the ultimate truth, put to frontier and open-weight AI models. Static site, hosted on Cloudflare Workers.

- `scripts/ask.py` asks the models and writes `site/answers.json`. Needs `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `XAI_API_KEY`. With no args it only asks models that don't have an answer yet; pass model ids to re-ask specific ones.
- `scripts/build.py` renders `site/index.html` from `scripts/template.html`.
- `site/` is served as static assets by a Cloudflare Worker (`wrangler.jsonc`). Deploy with `npx wrangler deploy`.
