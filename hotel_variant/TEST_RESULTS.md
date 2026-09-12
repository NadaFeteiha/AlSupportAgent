# Hotel Agent — Test Results

Ran the same 6 scenarios from the main project against this hotel-themed
agent instead, just with hotel data. All commands below were run for real
against the deployed agent.

Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/hotel_support_agent-1XO7TM4Zzc`

## Test 1 — Reservation Tracking

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Can you check reservation RES-001?", "customer_id": "GUEST-123", "session_id": "h1"}'
```
Got back the room type (Ocean View Suite), hotel name, check-in/out dates,
nightly rate, and total. All correct.

## Test 2 — Cancellation Processing

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "I need to cancel my Standard Room reservation RES-002 because of a change of plans. Please process the cancellation and refund.", "customer_id": "GUEST-123", "session_id": "h2b"}'
```
Got a cancellation ID (CXL-HO5YLYYT), a processed status, and the "3-5
business days" refund message. On my first try the agent asked me for a
cancellation reason before doing anything, which is fine, it just meant I
had to include the reason in the prompt to get it done in one shot.

## Test 3 — Knowledge Base (RAG)

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "What are the benefits of the Platinum guest rewards tier?", "customer_id": "GUEST-123", "session_id": "h3"}'
```
Got free breakfast, 15% discount on stays, and priority guest support, all
pulled straight from the knowledge base content.

## Test 4 — Long-Term Memory (two sessions)

Used a fresh guest ID (`GUEST-DEMO1`) instead of `GUEST-123` for this one, so
old test memory wouldn't get mixed in with a clean recall demo.

Session A:
```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Hi, I am Nada Feteiha. I prefer concise responses.", "customer_id": "GUEST-DEMO1", "session_id": "h-s-A"}'
```
"Hello Nada! I'll keep my responses concise..."

Session B (waited about a minute and a half for memory extraction, brand new
session, same guest ID):
```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Do you remember my name and communication preference?", "customer_id": "GUEST-DEMO1", "session_id": "h-s-B-retry"}'
```
"Yes, Nada Feteiha. I remember you prefer concise responses." My first
attempt at session B only waited 80 seconds and came back empty, extraction
just hadn't finished yet. Waiting longer fixed it.

## Test 5 — Guest Rewards / Stay Credit Calculation

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "I am a Gold member with 4250 points. Calculate my stay credit on a $150 standard room stay.", "customer_id": "GUEST-123", "session_id": "h5-retry"}'
```
Got the exact right numbers: 4,000 points redeemed, 10% tier discount, final
total $99.00, total savings $51.00, 99 points earned, 349 points remaining.

Worth mentioning: my first attempt at this exact prompt came back with wrong
numbers ($95 final total instead of $99), even though I'd already confirmed
the tool computes the right answer every time when I call it directly, and a
full local run of the agent also gave the correct $99. Retrying the same
prompt on the deployed agent gave the correct numbers. So this looks like the
model occasionally getting the numbers wrong when it writes up the final
answer, not a bug in the tool or my code.

## Test 6 — Browser Tool

```
agentcore invoke --session-id <uuid> \
  '{"prompt": "Go to https://www.udacity.com and tell me the page title.", "customer_id": "GUEST-123", "session_id": "h6"}'
```
"Learn the Latest Tech Skills; Advance Your Career | Udacity" — correct.
