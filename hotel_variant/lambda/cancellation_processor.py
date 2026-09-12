"""
Cancellation Processor Lambda
==============================
Handles cancellation-related operations for the hotel support agent.
Invoked directly by the AgentCore Gateway (not through API Gateway).

Tool routing works the same way as the refund-processor this is based on:
the Gateway passes the tool name in the Lambda client context under
"bedrockAgentCoreToolName", formatted as "TargetName___toolName".

Tools handled:
  initiate_cancellation    — cancel a reservation and confirm any refund
  check_cancellation_status — look up the status of an existing cancellation
  get_cancellation_policy  — return the cancellation window for a reservation
"""
import json
import random
import string
from datetime import datetime


def _new_cancellation_id() -> str:
    return "CXL-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def lambda_handler(event, context):
    raw_tool = ""
    if context.client_context and context.client_context.custom:
        raw_tool = context.client_context.custom.get("bedrockAgentCoreToolName", "")

    tool = raw_tool.split("___", 1)[-1] if "___" in raw_tool else raw_tool

    print(f"Tool called: {tool} | Event: {json.dumps(event)}")

    if tool == "initiate_cancellation":
        return {
            "statusCode": 200,
            "body": json.dumps({
                "cancellation_id": _new_cancellation_id(),
                "reservation_id": event.get("reservation_id"),
                "status": "CONFIRMED",
                "refund_amount": event.get("refund_amount", 0),
                "message": "Cancellation confirmed. Refund appears in 3-5 business days.",
                "created_at": datetime.utcnow().isoformat(),
            }),
        }

    if tool == "check_cancellation_status":
        return {
            "statusCode": 200,
            "body": json.dumps({
                "cancellation_id": event.get("cancellation_id"),
                "status": "PROCESSED",
                "eta": "2-3 business days",
            }),
        }

    if tool == "get_cancellation_policy":
        reservation_id = event.get("reservation_id", "")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "reservation_id": reservation_id,
                "free_cancellation_until": "48 hours before check-in",
                "late_cancellation_fee": "one night's rate",
            }),
        }

    return {
        "statusCode": 400,
        "body": json.dumps({"error": f"Unknown tool: {tool}"}),
    }
