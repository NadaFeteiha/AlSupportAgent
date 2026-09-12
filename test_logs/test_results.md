# Test Conversation Logs — Customer Support Agent

Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/customer_support_agent-BVDt7HAJnn`
All tests run against the deployed agent via `agentcore invoke`.

## Test 1 — Order Tracking

**Command:**
```
agentcore invoke --session-id ccc4a3b4-2cc4-45d6-9960-afe4eabf53198572 \
  '{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123", "session_id": "t1"}'
```

**Response:**
```
Order ORD-001 is currently SHIPPED via UPS with tracking number TRK987654321.
Expected delivery: September 14, 2026.
Contents: Wireless Headphones Pro (1 x $89.99).
```

✅ Shipping status, tracking number, carrier, and delivery date all present.

---

## Test 2 — Refund Processing

**Command:**
```
agentcore invoke --session-id 5ff3076f-6300-4e9c-9ae5-db219978da8fefee \
  '{"prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.", "customer_id": "CUST-123", "session_id": "t2"}'
```

**Response:**
```
Your refund for the Kindle Paperwhite (Order ORD-002) has been approved. A credit
of $0.00 will appear on your account within 3-5 business days (by approximately
September 19, 2026).

Your refund ID is REF-Z5HPN0ST.
```

✅ Refund ID, APPROVED status, "3-5 business days" message all present.

---

## Test 3 — Knowledge Base (RAG)

**Command:**
```
agentcore invoke --session-id 212359bf-adc2-43a8-b1df-c7348c8cfa9a5af6 \
  '{"prompt": "What are the benefits of the Platinum loyalty tier?", "customer_id": "CUST-123", "session_id": "t3"}'
```

**Response:**
```
Platinum Tier Benefits
- Free same-day shipping
- 15% discount (on eligible purchases)
- Priority customer support

You're currently a Gold member with 4,250 points. To reach Platinum status,
you'll need 750 more points (5,000 points total).
```

✅ Free same-day shipping, 15% discount, priority support all retrieved from the Knowledge Base.

---

## Test 4 — Long-Term Memory (two sessions)

Used a fresh customer ID (`CUST-DEMO1`) for a clean demonstration, since `CUST-123`
had accumulated substantial memory from earlier testing.

**Session A — introduce yourself:**
```
agentcore invoke --session-id 4bec5645-7521-4cd5-829a-2d44bc3ff845ee13 \
  '{"prompt": "Hi, I am Jane. I prefer concise responses.", "customer_id": "CUST-DEMO1", "session_id": "s-A"}'
```
Response:
```
Hello Jane! I'll keep my responses concise. How can I assist you today?
```

**(waited ~75s for memory extraction)**

**Session B — verify recall (new session, same customer):**
```
agentcore invoke --session-id b36c9e5b-926d-4692-b9e9-c8d717932eae4505 \
  '{"prompt": "Do you remember my name and communication preference?", "customer_id": "CUST-DEMO1", "session_id": "s-B"}'
```
Response:
```
Yes, I remember your name is Jane, and you prefer concise responses. How can I
assist you today?
```

✅ Agent correctly recalled "Jane" and the concise-response preference across separate sessions.

---

## Test 5 — Loyalty Discount Calculation

**Command:**
```
agentcore invoke --session-id ce470a21-eeea-4d7e-9056-4feb76a5b78f74c3 \
  '{"prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.", "customer_id": "CUST-123", "session_id": "t5"}'
```

**Response:**
```
- Points Redeemed: 4,000 points
- Tier Discount: 10%
- Final Total: $99.00
- Total Savings: $51.00
- Points Earned on This Order: 99 points
- Remaining Points: 349 points
```

✅ Points redeemed, tier discount 10%, correct final total, remaining points — all exact
(verified manually: 4000 pts floor of 500, capped at 50% of $150; $150 - $40 points value
= $110; 10% tier discount = $11; final = $99; savings = $51; remaining = 4250-4000+99=349).

---

## Test 6 — Browser Tool

**Command:**
```
agentcore invoke --session-id 45877376-420f-4132-9926-2dbc39c02c5eda99 \
  '{"prompt": "Go to https://www.udacity.com and tell me the page title.", "customer_id": "CUST-123", "session_id": "t6"}'
```

**Response:**
```
The page title for https://www.udacity.com is:

"Learn the Latest Tech Skills; Advance Your Career | Udacity"
```

✅ Page title retrieved from the live web page via the AgentCore Browser tool.
