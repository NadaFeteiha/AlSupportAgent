# Hotel Guest Support Agent (bonus variant)

The project suggested personalizing the agent to a different domain as an
optional extra, so I built this — same agent, same architecture, just
reworked for a hotel instead of an online store. This is NOT my graded
submission, that's still the e-commerce agent in `../starter/main.py`. I kept
this completely separate on purpose so I wouldn't risk breaking anything that
was already working and tested.

Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/hotel_support_agent-1XO7TM4Zzc`

## How it maps to the original

| E-commerce agent | Hotel agent |
|---|---|
| Order tracking | Reservation tracking |
| Refund processing | Cancellation processing |
| Product/policy Knowledge Base | Room/amenity/policy Knowledge Base |
| Loyalty discount on a purchase | Guest rewards credit on a stay |
| Customer memory | Guest memory |
| Browser tool | Browser tool (didn't change this one at all) |

Same 8 pieces: app init, config, model/clients, namespace helper, memory
hook, KB search tool, discount/credit tool, entrypoint. Same Gateway +
Memory + Knowledge Base + Code Interpreter + Browser setup. I basically just
copied `main.py`, renamed things, and swapped in hotel data.

Full test results are in [`TEST_RESULTS.md`](TEST_RESULTS.md).

## AWS resources for this one

| Resource | Value |
|---|---|
| Lambda (reservations) | `reservation-tracker` |
| Lambda (cancellations) | `cancellation-processor` |
| API Gateway REST API | `vppxyvovqh`, stage `prod` |
| AgentCore Gateway | `hotelsupportgateway-7jozdankci`, 2 targets, 6 MCP tools |
| Knowledge Base | `HotelSupportKB`, ID `YVH9GPFJLR` |
| AgentCore Memory | `HotelSupportMemory-42pLIbBtwu`, strategies `guest_facts` and `guest_preferences` |
| AgentCore Runtime | `hotel_support_agent-1XO7TM4Zzc` |

One small thing worth mentioning: for the main e-commerce KB I had to use the
AWS console because my account isn't allowed to create OpenSearch Serverless
collections directly through the CLI. For this one I found that the newer
"Managed" knowledge base type (`knowledgeBaseConfiguration.type = MANAGED`)
can be created straight through the `bedrock-agent` API without touching
OpenSearch at all, so this whole KB was set up without ever opening the
console.

## Try it yourself

```bash
cd hotel_variant
uv sync
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Can you check reservation RES-001?", "customer_id": "GUEST-123", "session_id": "h1"}'
```

Sample data (hard-coded in `lambda/reservation_tracker.py`, same as the
e-commerce Lambdas):
- `RES-001` — Ocean View Suite, checked in, guest `GUEST-123`
- `RES-002` — Standard Room, completed stay, guest `GUEST-123`
- `RES-003` — Deluxe Room, upcoming, guest `GUEST-456`
- `GUEST-123` — Alice Johnson, Gold tier, 3,200 points
- `GUEST-456` — Bob Lee, Silver tier, 450 points

## One thing I noticed while testing

On one run of the stay-credit test, the agent's final answer had the wrong
numbers ($95 instead of the correct $99), even though I checked and the tool
itself was computing the right answer every single time I tested it directly.
Running the exact same prompt again gave the correct numbers. My best guess
is the model occasionally messes up when it's paraphrasing a correct tool
result into a nice sentence, rather than an actual bug in the code. More
detail in `TEST_RESULTS.md`.
