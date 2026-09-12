# Reflection

**Design decision.** For `calculate_loyalty_discount`, I run the arithmetic
entirely inside the Code Interpreter sandbox rather than letting the LLM compute
the discount from a prompt. Loyalty points redeem in blocks of 500, capped at 50%
of the order total, with a separate tier discount applied afterward — a sequence
of floor/min operations an LLM can plausibly round or drop a step on.
Generating a Python code string and executing it via `code_session(...).invoke()`
guarantees identical input always produces identical output, which matters when
the number on screen is a real dollar amount. I validated the formula's constants
against the product catalog itself (retrieved via the Knowledge Base: "100 points
= $1, minimum redemption 500 points") rather than guessing them.

**Challenge.** The browser tool worked in isolation but appeared to hang forever
when called from inside the async `invoke()` entrypoint alongside the Gateway's
MCP client. Using `faulthandler.dump_traceback_later()` to get a live stack trace
of the "hung" process showed the agent had already produced the correct answer —
the hang was in `Browser.__del__`, deadlocked in a nested event loop during
garbage collection. Root cause: I was instantiating a fresh `AgentCoreBrowser`
per request, and its destructor ran the moment the object went out of scope at
the end of `invoke()`. Moving the browser to a single module-level instance
(matching how the model and memory client are initialized) eliminated the
repeated construct/destruct cycle entirely.

**Extending for production.** Two gaps stood out that I'd close before running
this for real customers. First, `retrieve_customer_context` pulls the top-k
memories by embedding similarity with no relevance threshold; once enough
interactions accumulate for one actor ID, semantically-similar but off-topic
memories get injected into unrelated prompts and skew responses. I'd add a
minimum similarity-score cutoff and a job to expire or summarize old records so
context injection stays scoped to the current turn. Second, AWS calls (Gateway,
Memory, Knowledge Base) currently fail outright on a single transient error — I
saw this firsthand when a freshly-attached IAM policy took a minute to
propagate and identical requests failed then succeeded with no code change. I'd
wrap these in retry-with-backoff and lean on AgentCore's built-in OpenTelemetry
spans for tracing, so a transient AWS-side hiccup doesn't surface as a
customer-facing error. I'd also swap the NONE authorizer for IAM or OAuth before handling real customer
data, and add CloudWatch alarms on error rate and token spend to catch
regressions early.
