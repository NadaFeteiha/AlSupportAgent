# Project: Building a Production-Grade Customer Support AI Agent with Amazon Bedrock AgentCore

**Udacity — AWS AI Engineering Nanodegree — Course 2**

---

## ✅ Project Status: Complete & Deployed

All 8 TODO sections in `starter/main.py` are implemented, the agent is deployed to
Amazon Bedrock AgentCore Runtime, and all 6 required test scenarios have been
verified against the live deployed agent.

- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:092134045103:runtime/customer_support_agent-BVDt7HAJnn`
- **Test results:** [`test_logs/test_results.md`](test_logs/test_results.md)
- **Written reflection:** [`REFLECTION.md`](REFLECTION.md)

---

## Overview

In this project you will build a fully functional, production-ready AI customer support agent for a fictional Amazon store. Starting from a simple local chatbot, you will progressively add cloud infrastructure, external tool integration, a knowledge base, persistent memory, a code interpreter, and a browser — finishing with a deployable agent that can handle real customer inquiries end-to-end.

By the end of the project your agent will be able to:

- Answer questions about products, return policies, and loyalty rewards using Retrieval-Augmented Generation (RAG)
- Look up order status and process refunds by calling Lambda functions through the AgentCore Gateway
- Remember customer preferences and conversation history across multiple sessions
- Calculate exact loyalty discounts using a secure code sandbox
- Navigate websites to fetch live information

---

## Learning Objectives

After completing this project you will be able to:

1. Deploy an AI agent to Amazon Bedrock AgentCore
2. Wire up external Lambda tools via the AgentCore Gateway using the Model Context Protocol (MCP)
3. Implement RAG with a Bedrock Knowledge Base
4. Add short-term (session) and long-term (cross-session) memory using AgentCore Memory
5. Use the AgentCore Code Interpreter for precise computation
6. Integrate the AgentCore Browser tool for live web access
7. Monitor and observe agent behaviour with Amazon CloudWatch

---

## Prerequisites

### AWS Account

- An active AWS account with permission to create and manage:
  - IAM roles and policies
  - Lambda functions
  - API Gateway REST APIs
  - Amazon Bedrock Knowledge Bases (with S3 and OpenSearch access)
  - Amazon Bedrock AgentCore resources (Runtime, Gateway, Memory)
  - Amazon CloudWatch
- All resources should be created in **us-east-1** (N. Virginia) unless stated otherwise.

### Local Development Environment

| Tool | Version |
|------|---------|
| Python | 3.14+ |
| [uv](https://docs.astral.sh/uv/) | Latest |
| AWS CLI | v2 |
| AgentCore CLI (`agentcore`) | Installed via the starter-toolkit |
| Node.js (for MCP Inspector) | 18+ |

### Model Access

Enabled model in the Amazon Bedrock console under **Model access**:

- **Amazon Nova Lite** (`global.amazon.nova-2-lite-v1:0`)

---

## Project Structure

```
project/
├── README.md                ← this file
├── REFLECTION.md             ← written reflection (design decision, challenge, production)
├── test_logs/
│   └── test_results.md       ← command + real output for all 6 test scenarios
└── starter/
    ├── main.py                ← completed agent (all 8 TODOs implemented)
    ├── pyproject.toml
    ├── product_catalog.txt    ← uploaded to S3 / synced into the Knowledge Base
    └── lambda/
        ├── order_tracker.py     ← deployed as-is to AWS Lambda
        ├── refund_processor.py  ← deployed as-is to AWS Lambda
        └── lambda_schema         ← JSON schema used to register refund_processor as a Gateway tool
```

---

## Part 1 — AWS Infrastructure (as actually deployed)

| Resource | Value |
|---|---|
| Region | `us-east-1` |
| Lambda: order tracking | `order-tracker` |
| Lambda: refunds | `refund-processor` |
| API Gateway REST API | `chcb0zkb9b` (stage `prod`) |
| AgentCore Gateway | `customersupportgateway-zh3m74vmjj` (NONE authorizer, 2 targets: `order-tracker` API Gateway target, `refund-processor` Lambda target — 6 MCP tools total) |
| Knowledge Base | `CustomerSupportKB` — ID `USCGD9ZEJ1` (Managed embeddings, S3 data source `cs-agent-kb-092134045103-68312`) |
| AgentCore Memory | `CustomerSupportMemory-L1eStICBN4` (strategies: `customer_facts` (SEMANTIC), `customer_preferences` (USER_PREFERENCE)) |
| AgentCore Runtime | `customer_support_agent-BVDt7HAJnn` (Direct Code Deploy, Python 3.11) |

**Verify Gateway tools:**
```bash
npx @modelcontextprotocol/inspector
# Connect to the Gateway URL, confirm all 6 tools are listed:
#   order-tracker___get_order, order-tracker___get_customer_orders,
#   order-tracker___get_customer, refund-processor___initiate_refund,
#   refund-processor___check_refund_status, refund-processor___get_return_label
```

**Verify Knowledge Base directly:**
```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id USCGD9ZEJ1 \
  --retrieval-query '{"text": "What is the return policy for electronics?"}' \
  --region us-east-1
# Expected: mentions the 15-day return window for electronics
```

---

## Part 2 — The Agent (`starter/main.py`)

All 8 TODOs are implemented:

1. **App init** — `BedrockAgentCoreApp` instance
2. **Configuration** — `GATEWAY_URL`, `KB_ID`, `REGION`, `MEMORY_ID` (env-var overridable, real values as defaults)
3. **Model & clients** — `BedrockModel` (Nova Lite), `MemoryClient`, boto3 `bedrock-agent-runtime` client, module-level `AgentCoreBrowser`
4. **`get_namespaces()`** — maps memory strategy type → namespace template
5. **`MemoryHook`** — retrieves relevant memories before each turn, saves the (query, response) pair after
6. **`search_knowledge_base`** — calls the Knowledge Base `Retrieve` API
7. **`calculate_loyalty_discount`** — exact arithmetic via AgentCore Code Interpreter, with a tier-only fallback
8. **`invoke()` entrypoint** — wires memory, browser, KB, discount, and Gateway MCP tools into one `Agent` call

Deploy commands used:
```bash
cd starter
uv sync
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore configure --entrypoint main.py --name customer_support_agent
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore deploy
```

---

## Part 3 — Functional Testing

All 6 scenarios below have already been run against the deployed agent — see
[`test_logs/test_results.md`](test_logs/test_results.md) for the full commands and real responses.

### To take your own screenshots for submission

Run each command below **in your own terminal** (from the `starter/` directory) and
screenshot the terminal window showing the command and its `Response:` output.
Each command generates a fresh session ID automatically via `uuidgen` (AgentCore
requires session IDs of 33+ characters) — run them one at a time, in order.

**Test 1 — Order Tracking**
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123", "session_id": "t1"}'
```
📸 Screenshot this output.

**Test 2 — Refund Processing**
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.", "customer_id": "CUST-123", "session_id": "t2"}'
```
📸 Screenshot this output.

**Test 3 — Knowledge Base (RAG)**
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "What are the benefits of the Platinum loyalty tier?", "customer_id": "CUST-123", "session_id": "t3"}'
```
📸 Screenshot this output.

**Test 4 — Long-Term Memory (both sessions required)**

Use a customer ID that hasn't accumulated a lot of prior memory (e.g. a fresh
one like `CUST-DEMO-<yourname>`) so the recall is clean and unambiguous.

Session A — introduce yourself:
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Hi, I am Jane. I prefer concise responses.", "customer_id": "CUST-DEMO1", "session_id": "s-A"}'
```
📸 Screenshot this output.

Wait at least 60–90 seconds (memory extraction runs asynchronously), then Session B — verify recall in a brand-new session:
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Do you remember my name and communication preference?", "customer_id": "CUST-DEMO1", "session_id": "s-B"}'
```
📸 Screenshot this output too — you need **both** Session A and Session B screenshots for Test 4.

**Test 5 — Loyalty Discount Calculation**
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.", "customer_id": "CUST-123", "session_id": "t5"}'
```
📸 Screenshot this output.

**Test 6 — Browser Tool**
```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 agentcore invoke --session-id "$(uuidgen)" \
  '{"prompt": "Go to https://www.udacity.com and tell me the page title.", "customer_id": "CUST-123", "session_id": "t6"}'
```
📸 Screenshot this output. (This one can take up to a minute or two — the browser session has to spin up before it navigates.)

---

## Submission Checklist

- [x] `main.py` with all 8 TODOs completed (no `pass` or placeholder `None` remaining)
- [ ] Screenshots or terminal output for Test 1 — Order Tracking
- [ ] Screenshots or terminal output for Test 2 — Refund Processing
- [ ] Screenshots or terminal output for Test 3 — Knowledge Base (RAG)
- [ ] Screenshots or terminal output for Test 4 — Long-Term Memory (both sessions)
- [ ] Screenshots or terminal output for Test 5 — Loyalty Discount Calculation
- [ ] Screenshots or terminal output for Test 6 — Browser Tool
- [x] Written reflection (200–400 words) covering a design decision, a challenge, and a production consideration — see [`REFLECTION.md`](REFLECTION.md)

> Text-based terminal output for all 6 tests is already captured in
> `test_logs/test_results.md`. The checkboxes above are left unchecked because
> your mentor may specifically want your own screenshots — run the commands
> above in your terminal and screenshot each one if so.

---

## Helpful References

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents Documentation](https://strandsagents.com)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [uv Package Manager](https://docs.astral.sh/uv/)
