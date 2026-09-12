# Hotel Guest Support Agent (domain variant)

This is a second version of the customer support agent, built on the exact
same architecture as the main e-commerce submission (`../starter/main.py`),
just re-themed for a hotel instead of an online store. It's one of the
project's optional "stand out" suggestions — I kept the main e-commerce
agent as the actual graded submission and built this as a separate,
independently deployed variant so nothing about the original gets touched.

| E-commerce version | Hotel version |
|---|---|
| Order tracking | Reservation tracking |
| Refund processing | Cancellation processing |
| Product/policy Knowledge Base | Room/amenity/policy Knowledge Base |
| Loyalty discount on a purchase | Guest rewards credit on a stay |
| Customer memory | Guest memory |
| Browser tool | Browser tool (unchanged) |

Same 8 pieces of code (app init, config, model/clients, namespace helper,
memory hook, KB search tool, discount/credit tool, entrypoint), same Gateway
+ Memory + Knowledge Base + Code Interpreter + Browser pattern. Only the
Lambda data, the KB content, and some naming changed.

Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/hotel_support_agent-1XO7TM4Zzc`

Test results: [`TEST_RESULTS.md`](TEST_RESULTS.md)

## AWS resources for this variant

| Resource | Value |
|---|---|
| Lambda (reservations) | `reservation-tracker` |
| Lambda (cancellations) | `cancellation-processor` |
| API Gateway REST API | `vppxyvovqh`, stage `prod` |
| AgentCore Gateway | `hotelsupportgateway-7jozdankci`, 2 targets, 6 MCP tools |
| Knowledge Base | `HotelSupportKB`, ID `YVH9GPFJLR` (Managed embeddings type — created directly via the API this time, no console step needed) |
| AgentCore Memory | `HotelSupportMemory-42pLIbBtwu`, strategies `guest_facts` and `guest_preferences` |
| AgentCore Runtime | `hotel_support_agent-1XO7TM4Zzc` |

## Running it yourself

```bash
cd hotel_variant
uv sync
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Can you check reservation RES-001?", "customer_id": "GUEST-123", "session_id": "h1"}'
```

Sample guest/reservation data (hard-coded in `lambda/reservation_tracker.py`,
same pattern as the e-commerce Lambdas):
- `RES-001` — Ocean View Suite, checked in, guest `GUEST-123`
- `RES-002` — Standard Room, completed stay, guest `GUEST-123`
- `RES-003` — Deluxe Room, upcoming, guest `GUEST-456`
- `GUEST-123` — Alice Johnson, Gold tier, 3,200 points
- `GUEST-456` — Bob Lee, Silver tier, 450 points

## One thing worth knowing about

While testing Test 5 here, one run of the stay-credit calculation came back
with numbers that didn't match what the tool actually computed ($95 instead
of the correct $99), even though calling the tool directly and running the
full agent locally both gave the right answer every time. A retry on the
identical deployed request gave the correct numbers. This looks like the
model occasionally paraphrasing a correct tool result into slightly wrong
numbers rather than a bug in the code — see the note in `TEST_RESULTS.md` and
the main project's `REFLECTION.md`.
