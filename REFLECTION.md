# Reflection

**Design decision.** For `calculate_loyalty_discount`, I chose to run the arithmetic
entirely inside the Code Interpreter sandbox rather than let the LLM compute the
discount from a prompt. Loyalty points redeem in blocks of 500, capped at 50% of
the order total, with a separate tier discount applied afterward — a sequence of
floor/min operations where an LLM can plausibly "round" or drop a step. Delegating
this to a generated Python code string executed via `code_session(...).invoke()`
guarantees the same input always produces the same exact output, which matters
when the number on screen is a real dollar amount. I validated the formula against
the product catalog itself (retrieved via the Knowledge Base: "100 points = $1,
minimum redemption 500 points") rather than guessing constants.

**Challenge.** The browser tool worked in isolation but appeared to hang forever
when called from inside the async `invoke()` entrypoint alongside the Gateway's
MCP client. Using `faulthandler.dump_traceback_later()` to get a live stack trace
of the "hung" process revealed the agent had actually already produced the
correct answer — the hang was in `Browser.__del__`, deadlocked in a nested event
loop during garbage collection. The root cause: I was instantiating a fresh
`AgentCoreBrowser` per request, and its destructor ran the moment the object went
out of scope at the end of each `invoke()` call. Moving the browser to a single
module-level instance (matching how the Bedrock model and memory client are
already initialized) eliminated the repeated construct/destruct cycle entirely.

**Production consideration.** Testing surfaced two things I'd treat differently
in production. First, IAM policy changes on the runtime's execution role weren't
immediately consistent — identical requests failed and then succeeded a minute
later with no code change, which argues for retry-with-backoff around AWS calls
rather than assuming a single failure is permanent. Second, `retrieve_customer_context`
pulls the top-k memories by embedding similarity with no relevance threshold; after
enough unrelated interactions accumulate for one actor ID, semantically-similar
but off-topic memories get injected into unrelated prompts and visibly skew
responses. In production I'd add a minimum similarity-score cutoff and monitor
per-actor memory growth so context injection stays scoped to what's actually
relevant to the current turn.
