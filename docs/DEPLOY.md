# Deploying the demo to a Hugging Face Space

The public demo is a Docker Space on free CPU hardware. The image holds the code, the corpus and
the index; the language model is a hosted one, reached with an API key kept in the Space's secrets.
Nothing in this repository contains a key.

## What you need
- A Hugging Face account.
- An API key for a hosted model that LiteLLM supports. Any provider works: the app only reads
  `SMALL_MODEL`, `LARGE_MODEL` and the provider's key from the environment.

## Steps
1. On huggingface.co: **New Space** → SDK **Docker** → template **Blank** → hardware **CPU basic** → public.
2. In the Space's **Files** tab, upload the two files of [`deploy/space/`](../deploy/space):
   `Dockerfile` and `README.md` (replace the README the Space created). `check_index.py` is not
   uploaded; the image takes it from the repository.
3. In **Settings → Variables and secrets**:

   | Kind | Name | Value |
   |---|---|---|
   | Secret | the provider's key, e.g. `GEMINI_API_KEY` | your key |
   | Variable | `SMALL_MODEL` | e.g. `gemini/gemini-3.5-flash-lite` |
   | Variable | `LARGE_MODEL` | e.g. `gemini/gemini-3.8-flash` |
   | Variable (optional) | `DEMO_DAILY_LIMIT`, `DEMO_SESSION_LIMIT` | default 300 per day, 10 per visit |
   | Variable (optional) | `THREATLENS_REF` | a tag or commit to deploy instead of `main` |

4. The Space builds by itself (about 15 minutes: it downloads the pinned sources, embeds 6,000
   chunks on CPU and fetches the reranker). The build fails on purpose if a source was unreachable.
5. Open the Space, ask one of the example questions, and put the URL in the README.

To redeploy after a merge: **Settings → Factory rebuild**. A plain restart reuses the cached image
layer that cloned the repository.

## Choosing the model
Free tiers change often, so the model is configuration, not code. Checked against the providers'
own pages on 2026-11-11:
- **Google Gemini API**: the pricing page lists `gemini-3.5-flash-lite`, `gemini-3.6-flash` and
  `gemini-3.8-flash` as free of charge on the standard tier. Its free tier may use the content
  sent to improve Google's products.
- **Groq**: the rate-limit page lists `openai/gpt-oss-20b` and `openai/gpt-oss-120b`
  (`groq/openai/gpt-oss-20b` in LiteLLM, key `GROQ_API_KEY`). The Llama models older guides
  recommend are no longer in that table.

Check the provider's current page before you pick, and run one question after the build: a wrong
model name shows up as an error on the first answer, not at build time.

## What protects the key
- The key is a Space **secret**: it is injected as an environment variable at run time and is not
  in the image, the repository or the build logs.
- A free-tier key has no billing attached, so the worst case of abuse is a used-up daily quota.
  Do not put a paid key behind a public demo without a spending limit at the provider.
- `DEMO_SESSION_LIMIT` and `DEMO_DAILY_LIMIT` ([limits.py](../src/threatlens/limits.py)) cap the
  questions per visit and per UTC day for everybody. They live in memory and reset on restart:
  they bound a burst, they are not accounting.
- The demo shows a notice not to paste confidential data: it is a public page and the model is a
  third party's.

## What the free hardware costs
The Space has 2 shared vCPUs and no GPU. Embedding the question and reranking 30 candidates with
the cross-encoder take most of the wait before the first token (measured at 13 s on a laptop CPU,
see the streaming results in the README). A free Space also sleeps after a period without
visitors, and the first question after a wake-up reloads the models.

## Run the same image locally
```bash
docker build -f deploy/space/Dockerfile -t threatlens-space .
docker run --rm -p 7860:7860 -e GEMINI_API_KEY=... \
  -e SMALL_MODEL=gemini/gemini-3.5-flash-lite -e LARGE_MODEL=gemini/gemini-3.8-flash threatlens-space
```
