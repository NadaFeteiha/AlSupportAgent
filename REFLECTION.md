# Reflection

**Design decision.** For the loyalty discount tool, I decided to do all the
math inside the Code Interpreter instead of just asking the model to compute
it. The discount logic has a few steps — redeem points in blocks of 500, cap
that at 50% of the order, then apply the tier discount on what's left — and
that's exactly the kind of multi-step math an LLM can get slightly wrong or
round differently each time. Writing it as an actual Python string and running
it through `code_session(...).invoke()` means the same input always gives the
same output, no matter how the model is feeling that day. I also double
checked my constants (100 points = $1, 500 point minimum) against the product
catalog in the Knowledge Base instead of just guessing them.

**Challenge.** The browser tool was the hardest part. It worked fine on its
own, but when I called it from inside the agent's async entrypoint, the whole
process just hung with no error. I eventually used `faulthandler` to dump a
stack trace while it was "stuck" and realized the agent had actually already
returned the right answer — the hang was happening afterward, in the browser
tool's cleanup code (`__del__`), which spins up its own event loop. The
problem was that I was creating a brand new `AgentCoreBrowser` object on every
single request, so its cleanup was firing right when the request finished.
Moving it to a single instance created once at module load (same as the model
and memory client) fixed it completely.

**Production consideration.** If I were putting this in front of real
customers, the memory retrieval needs a relevance cutoff. Right now it just
grabs the top 5 memories by similarity with no minimum score, so after enough
unrelated conversations pile up for one customer, old irrelevant facts start
leaking into new answers. I'd add a similarity threshold and probably expire
old memories after a while. I'd also add retry/backoff around the AWS calls —
I actually hit this during testing, where a freshly attached IAM policy took
about a minute to propagate and the exact same request failed and then
succeeded with zero code changes. Right now that just surfaces as an error to the customer, which isn't great.
Lastly, the Gateway uses the NONE authorizer, fine for this sandbox but not
something I'd ship with real customer data behind it.
