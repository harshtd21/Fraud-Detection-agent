"""
=====================================================================
 TOOLS — the actions the agent is allowed to take
=====================================================================
WHAT THIS FILE IS:
Claude (the AI model) cannot touch a database, run code, or take real
actions by itself — it can only produce TEXT. "Tool use" is the
mechanism that bridges that gap:

  1. We tell Claude "here are some functions you can ask to run,
     and here's what each one does" (that description lives in
     agent.py, in the TOOLS list).
  2. Claude decides, based on reasoning, WHICH function to call and
     WITH WHAT arguments — but it does not run the function itself.
  3. This file (tools.py) is where the ACTUAL Python code for each
     function lives. Our own Python program (in agent.py's loop)
     calls these functions on Claude's behalf and sends the result
     back to Claude as text.

Think of Claude as a person giving instructions over the phone, and
this file as the person on the other end actually pressing the
buttons and reading back what happened.
=====================================================================
"""

import json
from mock_data import (
    KNOWN_PAYEES,
    LOGIN_HISTORY,
    CARD_ACTIVITY,
    FRAUD_PATTERNS,
    get_recent_transaction_count,
)


# ---------------------------------------------------------------------------
# TOOL 1: get_payee_history
# ---------------------------------------------------------------------------
# Claude calls this when it wants to know: "has this user paid this
# person/company before?" We look it up in mock_data's KNOWN_PAYEES
# dictionary and return the answer as a JSON string (Claude reads
# JSON text, not raw Python objects).
def get_payee_history(user_id: str, payee_name: str) -> str:
    known = KNOWN_PAYEES.get(user_id, [])
    return json.dumps({
        "payee_name": payee_name,
        "previously_paid": payee_name in known,
        "total_known_payees_for_user": len(known),
    })


# ---------------------------------------------------------------------------
# TOOL 2: check_login_anomaly
# ---------------------------------------------------------------------------
# Claude calls this to check: "does the user's most recent login look
# different from their normal pattern?" (new country, new device).
# This is the main signal used to detect account takeover.
def check_login_anomaly(user_id: str) -> str:
    profile = LOGIN_HISTORY.get(user_id)
    if not profile:
        return json.dumps({"error": "no login history for this user"})

    latest = profile["recent_logins"][-1]  # the most recent login entry
    anomaly = (
        latest["country"] != profile["usual_country"]
        or latest["device_id"] not in profile["usual_device_ids"]
    )
    return json.dumps({
        "latest_login_country": latest["country"],
        "usual_country": profile["usual_country"],
        "latest_login_device": latest["device_id"],
        "device_recognised": latest["device_id"] in profile["usual_device_ids"],
        "anomaly_detected": anomaly,
    })


# ---------------------------------------------------------------------------
# TOOL 3: check_transaction_velocity
# ---------------------------------------------------------------------------
# Claude calls this to check: "has this user made an unusually high
# number of payments recently?" Useful for spotting structuring
# (splitting money into many small transfers) or an escalating scam
# (several payments to the same new scammer in a short time).
def check_transaction_velocity(user_id: str, window_hours: int = 24) -> str:
    count = get_recent_transaction_count(user_id, window_hours)
    return json.dumps({
        "user_id": user_id,
        "window_hours": window_hours,
        "transaction_count_in_window": count,
        "elevated": count >= 3,  # simple threshold; a real system would tune this
    })


# ---------------------------------------------------------------------------
# TOOL 3b: check_card_activity
# ---------------------------------------------------------------------------
# Claude calls this to check for card-not-present fraud: small "test"
# transactions followed by a large one, and/or a purchase from a country
# that doesn't match the cardholder's usual activity.
def check_card_activity(user_id: str) -> str:
    profile = CARD_ACTIVITY.get(user_id)
    if not profile:
        return json.dumps({"error": "no card activity on file for this user"})

    txns = profile["recent_card_transactions"]
    small_txns = [t for t in txns if t["amount_gbp"] <= 5]
    large_txns = [t for t in txns if t["amount_gbp"] > 100]
    latest = txns[-1]

    return json.dumps({
        "test_transaction_pattern_detected": len(small_txns) >= 2 and len(large_txns) >= 1,
        "small_test_transaction_count": len(small_txns),
        "latest_transaction_amount_gbp": latest["amount_gbp"],
        "latest_transaction_country": latest["country"],
        "usual_country": profile["usual_country"],
        "country_mismatch": latest["country"] != profile["usual_country"],
    })


# ---------------------------------------------------------------------------
# TOOL 4: check_fraud_patterns
# ---------------------------------------------------------------------------
# Claude calls this to retrieve the whole fraud-typology knowledge
# base, so it can compare the scenario in front of it against known
# patterns (romance scam, account takeover, etc — see mock_data.py).
#
# NOTE FOR LEARNING: this is intentionally simple — we just hand back
# the entire list every time and let Claude do the matching by
# reasoning. In a bigger system with hundreds of typologies, you
# would instead do a RAG (retrieval-augmented generation) step here:
# search a vector database for the most relevant few patterns instead
# of returning everything. That's the natural "next upgrade" for this
# project.
def check_fraud_patterns(context_description: str) -> str:
    return json.dumps({"known_fraud_typologies": FRAUD_PATTERNS})


# ---------------------------------------------------------------------------
# TOOL 5: hold_transaction
# ---------------------------------------------------------------------------
# Claude calls this when it decides a payment is risky enough to pause
# (typically: a scam where the real user might still be talked out of
# it). This doesn't move any real money — it just returns a simulated
# "held" status, since this is a demo, not a production system.
def hold_transaction(transaction_id: str, reason: str, risk_level: str) -> str:
    return json.dumps({
        "transaction_id": transaction_id,
        "status": "held",
        "risk_level": risk_level,
        "reason": reason,
        "next_step": "Escalated for secondary review / user confirmation.",
    })


# ---------------------------------------------------------------------------
# TOOL 6: release_transaction
# ---------------------------------------------------------------------------
# Claude calls this when it decides a payment looks safe and should
# proceed as normal.
def release_transaction(transaction_id: str) -> str:
    return json.dumps({"transaction_id": transaction_id, "status": "released"})


# ---------------------------------------------------------------------------
# TOOL 7: escalate_to_human
# ---------------------------------------------------------------------------
# Claude calls this when the risk looks like the ACCOUNT itself may be
# compromised (not just the user being deceived). In that case, asking
# the "user" clarifying questions is pointless — the person typing
# might be the attacker, not the real account owner — so the right
# move is to hand off to a human analyst instead.
def escalate_to_human(transaction_id: str, summary: str) -> str:
    return json.dumps({
        "transaction_id": transaction_id,
        "status": "escalated_to_human",
        "summary": summary,
    })


# ---------------------------------------------------------------------------
# THE "PHONE BOOK": maps a tool's name (as a string) to the actual
# Python function that implements it. agent.py's loop uses this
# dictionary to look up and run whichever tool Claude asked for,
# by name, without needing a big if/elif chain.
# ---------------------------------------------------------------------------
TOOL_IMPLEMENTATIONS = {
    "get_payee_history": get_payee_history,
    "check_login_anomaly": check_login_anomaly,
    "check_transaction_velocity": check_transaction_velocity,
    "check_card_activity": check_card_activity,
    "check_fraud_patterns": check_fraud_patterns,
    "hold_transaction": hold_transaction,
    "release_transaction": release_transaction,
    "escalate_to_human": escalate_to_human,
}
