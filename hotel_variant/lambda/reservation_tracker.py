"""
Reservation Tracking Lambda
============================
Handles reservation and guest lookup for the hotel support agent.
Invoked through the AgentCore Gateway (REST API proxy integration).

Routes exposed:
  GET /reservations/{reservation_id}   — return a single reservation by ID
  GET /guests/{guest_id}/reservations  — return all reservations for a guest
  GET /guests/{guest_id}               — return guest loyalty profile

The data is hard-coded for demonstration purposes, same as the order-tracker
Lambda this is based on.
"""
import json
from datetime import datetime, timedelta


def _reservations():
    """Return the mock reservation database."""
    return {
        "RES-001": {
            "reservation_id": "RES-001",
            "guest_id": "GUEST-123",
            "status": "CHECKED_IN",
            "room_type": "Ocean View Suite",
            "hotel": "Bayfront Grand Hotel",
            "check_in": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "nightly_rate": 289.00,
            "total": 1156.00,
        },
        "RES-002": {
            "reservation_id": "RES-002",
            "guest_id": "GUEST-123",
            "status": "COMPLETED",
            "room_type": "Standard Room",
            "hotel": "Bayfront Grand Hotel",
            "check_in": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() - timedelta(days=27)).strftime("%Y-%m-%d"),
            "nightly_rate": 159.00,
            "total": 477.00,
        },
        "RES-003": {
            "reservation_id": "RES-003",
            "guest_id": "GUEST-456",
            "status": "UPCOMING",
            "room_type": "Deluxe Room",
            "hotel": "Bayfront Grand Hotel",
            "check_in": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d"),
            "nightly_rate": 199.00,
            "total": 597.00,
        },
    }


def _guests():
    """Return the mock guest database."""
    return {
        "GUEST-123": {"name": "Alice Johnson", "loyalty_points": 3200, "tier": "Gold"},
        "GUEST-456": {"name": "Bob Lee", "loyalty_points": 450, "tier": "Silver"},
    }


def _response(status_code: int, body: dict) -> dict:
    """Format a Lambda proxy-integration response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    """Main Lambda entry point (API Gateway proxy integration)."""
    print(f"Event: {json.dumps(event)}")

    resource = event.get("resource", "")
    method = event.get("httpMethod", "GET")
    params = event.get("pathParameters") or {}

    reservations = _reservations()
    guests = _guests()

    if resource == "/reservations/{reservation_id}" and method == "GET":
        reservation_id = params.get("reservation_id", "").upper()
        reservation = reservations.get(reservation_id)
        if not reservation:
            return _response(404, {"error": f"Reservation {reservation_id} not found"})
        return _response(200, reservation)

    if resource == "/guests/{guest_id}/reservations" and method == "GET":
        gid = params.get("guest_id", "").upper()
        result = [r for r in reservations.values() if r["guest_id"] == gid]
        if not result:
            return _response(404, {"error": f"No reservations found for {gid}"})
        return _response(200, {"guest_id": gid, "reservations": result})

    if resource == "/guests/{guest_id}" and method == "GET":
        gid = params.get("guest_id", "").upper()
        guest = guests.get(gid)
        if not guest:
            return _response(404, {"error": f"Guest {gid} not found"})
        return _response(200, guest)

    return _response(400, {"error": "Unrecognised route", "resource": resource})
