# Hotel Guest Support Agent — Test Results

Domain variant of the e-commerce customer support agent. Same architecture,
same 6 test scenarios, different data. Deployed as its own separate agent so
the original e-commerce submission stays untouched.

Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/hotel_support_agent-1XO7TM4Zzc`

## Test 1 — Reservation Tracking

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Can you check reservation RES-001?", "customer_id": "GUEST-123", "session_id": "h1"}'
```
Response confirmed: room type (Ocean View Suite), hotel, check-in/out dates,
nightly rate, total cost.

## Test 2 — Cancellation Processing

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "I need to cancel my Standard Room reservation RES-002 because of a change of plans. Please process the cancellation and refund.", "customer_id": "GUEST-123", "session_id": "h2b"}'
```
Response confirmed: cancellation ID (CXL-HO5YLYYT), processed status, refund
timeline mentioned ("3-5 business days").

## Test 3 — Knowledge Base (RAG)

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "What are the benefits of the Platinum guest rewards tier?", "customer_id": "GUEST-123", "session_id": "h3"}'
```
Response confirmed: free breakfast, 15% discount on stays, priority guest
support — all pulled from the Knowledge Base.

## Test 4 — Long-Term Memory (two sessions)

Used a fresh guest ID (`GUEST-DEMO1`) so the recall demo isn't muddied by
earlier test traffic on `GUEST-123`.

Session A:
```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Hi, I am Nada Feteiha. I prefer concise responses.", "customer_id": "GUEST-DEMO1", "session_id": "h-s-A"}'
```
Response: "Hello Nada! I'll keep my responses concise..."

Session B (waited for memory extraction, new session, same guest ID):
```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Do you remember my name and communication preference?", "customer_id": "GUEST-DEMO1", "session_id": "h-s-B-retry"}'
```
Response: "Yes, Nada Feteiha. I remember you prefer concise responses."

## Test 5 — Guest Rewards / Stay Credit Calculation

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "I am a Gold member with 4250 points. Calculate my stay credit on a $150 standard room stay.", "customer_id": "GUEST-123", "session_id": "h5-retry"}'
```
Response confirmed exact math: 4,000 points redeemed, 10% tier discount,
final total $99.00, total savings $51.00, 99 points earned, 349 points
remaining.

**Note:** the first attempt at this test gave visibly wrong numbers ($95 final
total instead of $99) even though the tool itself returned the correct
result — direct testing of `calculate_stay_credit()` and a local run of the
full agent both produced the correct $99 answer every time, so this looks
like the model occasionally restating tool numbers incorrectly rather than a
bug in the tool or the code. A retry on the same prompt gave the exact right
numbers. See `REFLECTION.md` in the main project for more on this.

## Test 6 — Browser Tool

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Go to https://www.udacity.com and tell me the page title.", "customer_id": "GUEST-123", "session_id": "h6"}'
```
Response: "Learn the Latest Tech Skills; Advance Your Career | Udacity"
