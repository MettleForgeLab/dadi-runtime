# DADI LLM Adapter (Deterministic Envelope + Capture)

This pack provides a small, provider-agnostic adapter that makes LLM calls **artifact-addressable**:

- canonical **request artifacts** (`llm_request-v1`)
- captured **response artifacts** (`llm_response-v1`)
- replay mode (inject captured response, no provider call)
- drift detection mode (compare live response vs captured response)

It is designed to work with the artifact store schema from the DADI artifact store/orchestrator packs (`artifacts` table).

## Artifact schemas (envelope)

### llm_request-v1 (canonical JSON)

Required fields:
- `schema_version`: `llm_request-v1`
- `provider`
- `model`
- `prompt_bundle_sha256`
- `toolchain_manifest_sha256`
- `input_hashes[]` (hashes of artifacts used to assemble context)
- `decoding` (temperature, top_p, max_tokens, etc.)
- `tools` (optional, function schema hash pointers)

### llm_response-v1 (canonical JSON wrapper + raw body)

- `schema_version`: `llm_response-v1`
- `request_sha256`
- `provider`
- `model`
- `body` (raw provider response text as a string, or base64 if you prefer)

The adapter stores both request and response as immutable artifacts addressed by SHA256.

## Modes

- `live`: call provider, capture artifacts
- `replay`: load response artifact by SHA and return it
- `drift`: call provider, compare new response SHA to expected response SHA, emit drift record if different

## SQL (optional)

`sql/llm_calls.sql` adds an `llm_calls` table linking request/response artifacts to stage runs (if you want it).

## Usage

You implement `ProviderClient.complete(request)` and pass it to `LLMAdapter`.

See `examples/` for a stub provider and orchestrator-stage usage pattern.
