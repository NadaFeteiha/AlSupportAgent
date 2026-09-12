"""
Hotel Guest Support AI Agent
=============================
Domain variant of the e-commerce customer support agent, built with the same
architecture: AgentCore Runtime, Gateway (MCP), Knowledge Base (RAG),
AgentCore Memory, Code Interpreter, and the AgentCore Browser tool. Only the
data and tool names changed — reservations instead of orders, cancellations
instead of refunds, stay credit instead of loyalty discount on a purchase.

Run locally (after filling in config values):
  uv run main.py '{"prompt": "Hello", "customer_id": "GUEST-123", "session_id": "s1"}'

Deploy to AgentCore:
  agentcore deploy

Invoke deployed agent:
  agentcore invoke '{"prompt": "Hello", "customer_id": "GUEST-123", "session_id": "s1"}'
"""

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict, Optional
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser
from strands.agent.conversation_manager import SummarizingConversationManager
from pydantic import BaseModel, ValidationError


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("HotelSupportAgent")

app = BedrockAgentCoreApp()

os.environ["BYPASS_TOOL_CONSENT"] = "true"

GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://hotelsupportgateway-7jozdankci.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
KB_ID       = os.environ.get("KB_ID", "YVH9GPFJLR")
REGION      = os.environ.get("REGION", "us-east-1")
MEMORY_ID   = os.environ.get("MEMORY_ID", "HotelSupportMemory-42pLIbBtwu")

model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)

memory_client = MemoryClient(region_name=REGION)

_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

# same reason as the e-commerce version: create this once here, not inside
# invoke(), or its cleanup code hangs the process on every request
agent_core_browser = AgentCoreBrowser(region=REGION)


def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type -> namespace template string."""
    strategies = mem_client.get_memory_strategies(memory_id)
    return {
        strategy["type"]: strategy.get("namespaceTemplates", strategy.get("namespaces"))[0]
        for strategy in strategies
    }


class MemoryHook(HookProvider):
    """Long-term memory hook for the hotel support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)

    @staticmethod
    def _is_plain_text_user_message(message: Dict) -> bool:
        if not message or message.get("role") != "user":
            return False
        content = message.get("content", [])
        return bool(content) and all("toolResult" not in block for block in content)

    @staticmethod
    def _message_text(message: Dict) -> str:
        return " ".join(block["text"] for block in message.get("content", []) if "text" in block)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        message = event.agent.messages[-1]

        if not self._is_plain_text_user_message(message):
            return

        user_query = self._message_text(message)
        if not user_query:
            return

        memory_lines = []
        for strategy_type, namespace_template in self.namespaces.items():
            namespace = namespace_template.format(actorId=self.actor_id)
            try:
                memories = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=namespace,
                    query=user_query,
                    top_k=5,
                )
            except Exception as e:
                logger.warning("Memory retrieval failed for namespace %s: %s", namespace, e)
                continue

            for memory in memories:
                text = memory.get("content", {}).get("text", "")
                if text:
                    memory_lines.append(f"[{strategy_type}] {text}")

        if memory_lines:
            context_block = "Guest Context:\n" + "\n".join(memory_lines)
            for block in message["content"]:
                if "text" in block:
                    block["text"] = f"{context_block}\n\n{block['text']}"
                    break

    def save_support_interaction(self, event: AfterInvocationEvent):
        messages = event.agent.messages

        guest_query = None
        agent_response = None

        for message in reversed(messages):
            if agent_response is None and message.get("role") == "assistant":
                text = self._message_text(message)
                if text:
                    agent_response = text
                continue
            if agent_response is not None and self._is_plain_text_user_message(message):
                text = self._message_text(message)
                if text:
                    guest_query = text
                    break

        if not guest_query or not agent_response:
            return

        try:
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[(guest_query, "USER"), (agent_response, "ASSISTANT")],
            )
        except Exception as e:
            logger.warning("Failed to save support interaction to memory: %s", e)

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


@tool
def search_hotel_policies(query: str) -> str:
    """
    Search hotel room types, amenities, cancellation policy, and the guest
    rewards program. Use this for questions about room features, cancellation
    windows, refund timelines, rewards tiers, and property amenities.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    if not KB_ID or KB_ID == "<kbid>":
        return "Knowledge base not configured."

    resp = _bedrock_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
    )

    results = resp.get("retrievalResults", [])
    if not results:
        return "No relevant information found in the knowledge base."

    chunks = [r["content"]["text"] for r in results if r.get("content", {}).get("text")]
    return "\n---\n".join(chunks)


class StayCreditResult(BaseModel):
    """Validated shape for what calculate_stay_credit hands back to the agent."""

    points_redeemed: int
    tier_discount_pct: float
    final_total: float
    total_savings: float
    points_earned: int
    remaining_points: int
    note: Optional[str] = None


@tool
def calculate_stay_credit(
    loyalty_points: int,
    tier: str,
    stay_total: float,
    room_category: str = "standard",
) -> str:
    """
    Calculate the guest rewards credit for a hotel stay using the AgentCore
    Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points: Guest's current points balance
        tier:           Guest tier - Silver, Gold, or Platinum
        stay_total:     Total stay cost in USD
        room_category:  standard, premium, or dining (affects earn rate)

    Returns:
        Full discount breakdown and final price
    """
    code = f"""
import json

earn_rates = {{"standard": 1, "premium": 2, "dining": 3}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

loyalty_points = {loyalty_points}
tier = "{tier}"
stay_total = {stay_total}
room_category = "{room_category}"

# Redeem points in blocks of 500 (1 point = $0.01 of value), capped at 50% of the stay total
POINT_VALUE = 0.01
POINT_BLOCK = 500

available_points = (loyalty_points // POINT_BLOCK) * POINT_BLOCK
max_redeemable_value = stay_total * 0.5

points_redeemed = available_points
points_redeemed_value = points_redeemed * POINT_VALUE
if points_redeemed_value > max_redeemable_value:
    points_redeemed = int((max_redeemable_value / POINT_VALUE) // POINT_BLOCK) * POINT_BLOCK
    points_redeemed_value = points_redeemed * POINT_VALUE

subtotal_after_points = stay_total - points_redeemed_value

tier_discount_pct = tier_rates.get(tier, 0.0)
tier_discount_amount = subtotal_after_points * tier_discount_pct

final_total = round(subtotal_after_points - tier_discount_amount, 2)
total_savings = round(points_redeemed_value + tier_discount_amount, 2)

earn_rate = earn_rates.get(room_category, 1)
points_earned = int(final_total * earn_rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "points_redeemed": points_redeemed,
    "tier_discount_pct": tier_discount_pct,
    "final_total": final_total,
    "total_savings": total_savings,
    "points_earned": points_earned,
    "remaining_points": remaining_points,
}}

print(json.dumps(result))
"""

    try:
        with code_session(REGION) as code_client:
            response = code_client.invoke(
                "executeCode",
                {"code": code, "language": "python", "clearContext": True},
            )

        raw_result = None
        for event in response.get("stream", []):
            if "result" in event:
                raw_result = event["result"]
                break

        if raw_result is None:
            raise RuntimeError("Code Interpreter returned no result event")

        stdout = raw_result.get("structuredContent", {}).get("stdout", "")
        parsed = json.loads(stdout)
        validated = StayCreditResult(**parsed)
        return validated.model_dump_json()

    except (ValidationError, json.JSONDecodeError) as e:
        logger.error("Code Interpreter result failed validation: %s", e)
        raise

    except Exception as e:
        logger.warning("Code Interpreter unavailable, falling back to tier-only discount: %s", e)
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        tier_discount_pct = tier_rates.get(tier, 0.0)
        final_total = round(stay_total * (1 - tier_discount_pct), 2)
        fallback = StayCreditResult(
            points_redeemed=0,
            tier_discount_pct=tier_discount_pct,
            final_total=final_total,
            total_savings=round(stay_total - final_total, 2),
            points_earned=0,
            remaining_points=loyalty_points,
            note="Fallback calculation: Code Interpreter unavailable, tier discount only.",
        )
        return fallback.model_dump_json()


@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) - the guest's message
      customer_id (str, optional) - unique guest identifier
      session_id  (str, optional) - session identifier; generated if absent
    """
    user_input = payload.get("prompt", "")
    actor_id = payload.get("customer_id", "anonymous")
    session_id = payload.get("session_id") or str(uuid.uuid4())

    try:
        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID,
        )
        tools = [search_hotel_policies, calculate_stay_credit, agent_core_browser.browser]

        system_prompt = (
            "You are a helpful, concise guest support agent for a hotel. "
            "Use the available tools to look up reservations, process "
            "cancellations, answer questions about rooms/amenities/policies, "
            "calculate guest rewards credit, and browse the web when needed. "
            "Always ground factual answers in tool results rather than "
            "guessing.\n\n"
            "When using the browser tool, call init_session first with a "
            "session_name made only of lowercase letters, digits, and hyphens "
            "(10-36 characters), like 'browser-session-1'. Reuse that same "
            "session_name for every navigate/evaluate call after that. If a "
            "tool call comes back with a validation error, fix it and try "
            "again instead of giving up."
        )

        gateway_client = MCPClient(lambda: streamable_http_client(GATEWAY_URL))

        with gateway_client:
            gateway_tools = gateway_client.list_tools_sync()
            tools.extend(gateway_tools)

            agent = Agent(
                model=model,
                tools=tools,
                hooks=[memory_hook],
                system_prompt=system_prompt,
                conversation_manager=SummarizingConversationManager(
                    preserve_recent_messages=8,
                    proactive_compression=True,
                ),
            )

            result = await agent.invoke_async(user_input)

        return result.message["content"][0]["text"]

    except Exception as e:
        logger.exception("Agent invocation failed")
        return f"Sorry, something went wrong while processing your request: {e}"


def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()
    # Uncomment the line below and comment app.run() for local CLI testing:
    # main()
