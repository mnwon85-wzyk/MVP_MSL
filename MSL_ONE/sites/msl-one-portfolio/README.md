# Published CVRM Worker source

This folder contains the public runtime port of the CVRM portfolio. It bundles page.html and worker/api.mjs into dist/server/index.js.

## Local checks and build

1. Install Node.js 24+ and run npm ci.
2. Run npm test, then npm run build.
3. The build script also emits the generated worker/index.mjs entry point.

Before building, supply .openai/hosting.json for your own Sites project. A new project must use its own project_id; account bindings are intentionally omitted from this repository. The hosting manifest for the existing publication is not required to read or review the application source. For direct Cloudflare hosting, use your own Wrangler configuration pointing to dist/server/index.js.

Optional LLM connection requires SESSION_ENCRYPTION_KEY in the hosting secret store: a base64-encoded random 32-byte AES key. Never place that value in source files. API keys belong to individual visitor sessions, encrypted in an HttpOnly Secure SameSite cookie with a one-hour lifetime; the server does not include a shared paid model key.

The public-source endpoints query PubMed, ClinicalTrials.gov and Google News RSS. Upstream availability and rate limits can affect searches. Uploaded documents are processed as bounded text excerpts. The source includes a synthetic PDF fixture for extraction tests.
