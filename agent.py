"""
=====================================================================
 THE AGENT — system prompt, tool schemas, and the reasoning loop
=====================================================================
This is the most important file to understand. It has 4 parts:

  PART A: SYSTEM_PROMPT   — written instructions telling Claude HOW
                             to think about fraud review.
  PART B: TOOLS            — a JSON "menu" describing each tool from
                             tools.py, so Claude knows they exist.
  PART C: run_live()       — the actual agent loop: talk to the real
                             Claude API and execute whatever tools it
                             asks for.
  PART D: run_demo()       — replays a PRE-RECORDED trace instead of
                             calling the API, so this project can be
                             explored for free (no API key needed).

RUN THIS FILE WITH:
  python agent.py --demo                     (free, no API key — runs all 7 scenarios)
  python agent.py --demo --no-color          (free, plain text, no colors)
  python agent.py --live romance_scam         (real API call, needs a key)
  python agent.py --live account_takeover     (real API call, needs a key)

  Available --live scenario names: romance_scam, investment_scam,
  impersonation_scam, invoice_fraud, structuring, card_not_present,
  account_takeover — one for every fraud typology in mock_data.py.
=====================================================================
"""

import os
import sys
import time
import json
import argparse

from tools import TOOL_IMPLEMENTATIONS
from demo_transcripts import DEMO_SCENARIOS
import colors

MODEL = "claude-sonnet-5"


# =====================================================================
# PART A: SYSTEM PROMPT
# =====================================================================
# This is plain English text that gets sent to Claude at the start of
# every conversation. It's not code — it's instructions, the same way
# you'd brief a new employee. Everything the agent "knows" about HOW
# to behave comes from this text, not from any hard-coded if/else logic.
#
# Notice it teaches Claude the KEY DISTINCTION of this whole project:
# scams (user is deceived -> hold + ask questions) vs. account
# takeover (account is compromised -> escalate to a human).
SYSTEM_PROMPT = """You are a fraud-prevention assistant for a fintech payments app. \
Your job is to review payments and account activity BEFORE damage is done, and \
decide whether to let a payment proceed, hold it, or escalate it to a human analyst.

Process for every review:
1. Gather context using the available tools: payee history, login anomalies, \
transaction velocity, and known fraud typologies. Only call the tools relevant \
to the scenario you've been given.
2. Reason explicitly about which fraud typology (if any) this resembles, and how \
strongly, distinguishing between:
   - Authorised push payment (APP) scams, where the user is being deceived into \
sending money themselves — these usually warrant a hold + clarifying questions.
   - Unauthorised fraud (e.g. account takeover, card-not-present fraud), where the \
account or card itself may be compromised — these usually warrant escalation to a \
human analyst, since the person you're talking to may not be the genuine user.
   - Structuring/money-laundering patterns — usually warrant a hold + escalation.
3. If risk is LOW: call release_transaction and briefly explain your confidence.
4. If risk is MEDIUM/HIGH and it looks like the user is being scammed: call \
hold_transaction with a clear reason, and ask 1-3 short, calm clarifying questions.
5. If risk is HIGH and it looks like account/card compromise rather than user \
deception: call escalate_to_human with a clear summary.

Never assert fraud with certainty — you are surfacing risk, not issuing a verdict. \
Explain your reasoning in plain English a non-technical user could follow in one read."""


# =====================================================================
# PART B: TOOL SCHEMAS
# =====================================================================
# This is a JSON description of every function in tools.py — it tells
# Claude the tool's NAME, what it DOES (description), and what
# ARGUMENTS it needs (input_schema). Claude reads this list once at
# the start and uses it to decide which tool to call and how to call
# it correctly. This list must stay in sync with the actual Python
# functions in tools.py — if you add a new function there, add a
# matching entry here too, or Claude won't know it exists.
TOOLS = [
    {
        "name": "get_payee_history",
        "description": "Check whether the user has paid this payee before. First-time payees carry higher risk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "payee_name": {"type": "string"},
            },
            "required": ["user_id", "payee_name"],
        },
    },
    {
        "name": "check_login_anomaly",
        "description": "Compare the user's most recent login (country, device) against their usual pattern. Used to detect account takeover.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "check_transaction_velocity",
        "description": "Count recent payments by this user in a time window. High counts suggest structuring or an escalating scam.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "window_hours": {"type": "integer"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "check_card_activity",
        "description": "Check recent card transactions for a test-transaction pattern (small purchases followed by a large one) and country mismatches. Used to detect card-not-present fraud.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "check_fraud_patterns",
        "description": "Retrieve the known fraud typology knowledge base (APP scams, account takeover, card fraud, structuring) to compare against this scenario's context.",
        "input_schema": {
            "type": "object",
            "properties": {"context_description": {"type": "string"}},
            "required": ["context_description"],
        },
    },
    {
        "name": "hold_transaction",
        "description": "Place a cooling-off hold on a payment pending further review or user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string"},
                "reason": {"type": "string"},
                "risk_level": {"type": "string", "enum": ["medium", "high"]},
            },
            "required": ["transaction_id", "reason", "risk_level"],
        },
    },
    {
        "name": "release_transaction",
        "description": "Release/approve a payment to proceed normally.",
        "input_schema": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string"}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand off to a human fraud analyst when this looks like account/card compromise rather than a scam the user can be talked through.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["transaction_id", "summary"],
        },
    },
]


# The full set of example scenarios that get sent to Claude as the FIRST
# message in the conversation, in --live mode. This is what kicks off the
# agent loop below. There are 7 here — one for each fraud typology in
# mock_data.py's FRAUD_PATTERNS list — so the project covers a genuinely
# comprehensive spread rather than just one or two examples.
SCENARIO_PROMPTS = {
    "romance_scam": (
        "User user_123 wants to send 800 GBP to a payee called 'Alex Rivera' "
        "(transaction id txn_001). This is a first payment to this payee. "
        "The user's payment note says: 'sending this to help my partner with a "
        "flight - we met on a dating app 6 weeks ago and haven't met in person "
        "yet, he needs this urgently for a visa fee.' Review this payment."
    ),
    "investment_scam": (
        "User user_123 is sending a third payment in 48 hours to a payee "
        "called 'CoinSurge Capital' (transaction id txn_003), an amount of "
        "1,200 GBP. The user found this platform via an Instagram ad "
        "promising guaranteed 40% monthly returns. Review this payment."
    ),
    "impersonation_scam": (
        "User user_123 wants to send their full balance, 3,000 GBP, to a "
        "new payee called 'Secure Holding Account' (transaction id txn_004). "
        "The user says they received a phone call from someone claiming to "
        "be their bank's fraud team, who said their account was compromised "
        "and they needed to move funds to a 'safe account' immediately, and "
        "warned them not to hang up. Review this payment."
    ),
    "invoice_fraud": (
        "User user_123 wants to pay a new supplier, 'Bright Peak Traders' "
        "(transaction id txn_005), 2,400 GBP for equipment. The seller has "
        "no reviews, insisted on a direct bank transfer instead of the "
        "marketplace's checkout, and the price is noticeably below market "
        "rate. Review this payment."
    ),
    "structuring": (
        "User user_123 has made 4 payments to 4 different new payees in the "
        "last 6 hours, each just under 1,000 GBP (a common reporting "
        "threshold). The latest is to 'Orion Freight Co' (transaction id "
        "txn_006). Review this activity."
    ),
    "card_not_present": (
        "User user_123's card shows two small transactions of 1-2 GBP in "
        "the last two hours, followed by a 650 GBP purchase at an "
        "electronics store in a country the card has never been used in "
        "before (transaction id txn_007). Review this card activity."
    ),
    "account_takeover": (
        "User user_123 just logged in and immediately initiated a large payment "
        "of 4,500 GBP to a new payee called 'Quicksilver Holdings' "
        "(transaction id txn_002). Review this login and payment."
    ),
}


# =====================================================================
# PART C: run_demo() — free, no API key, no network calls
# =====================================================================
def run_demo(scenario_key: str) -> None:
    """
    Print a PRE-RECORDED trace (from demo_transcripts.py) step by
    step, with small pauses so it's readable, like watching a replay
    of a real run. This function never contacts the Claude API.
    """
    scenario = DEMO_SCENARIOS[scenario_key]
    print("\n" + colors.header(f"{'=' * 70}\nDEMO MODE — scenario: {scenario_key}\n"
                                f"{scenario['description']}\n{'=' * 70}"))
    for step in scenario["trace"]:
        kind = step[0]
        if kind == "text":
            print("\n" + colors.agent_line(step[1]))
        elif kind == "tool_call":
            _, name, args = step
            print("\n" + colors.tool_call_line(f"{name}({json.dumps(args)})"))
        elif kind == "tool_result":
            print(colors.tool_result_line(step[1]))
        time.sleep(0.4)  # purely cosmetic pacing, not required
    print("\n" + colors.footer_note(
        f"{'=' * 70}\n(This was a recorded trace. Run with --live {scenario_key} "
        f"to execute this against the real Claude API instead.)\n{'=' * 70}\n"))


# =====================================================================
# PART D: run_live() — THE ACTUAL AGENT LOOP (real API calls)
# =====================================================================
def run_live(scenario_key: str, max_turns: int = 8) -> None:
    """
    This is the real thing. Walk through the comments in order —
    this loop IS what "an agent" means in practice.
    """
    try:
        import anthropic
    except ImportError:
        sys.exit("The 'anthropic' package isn't installed. Run: pip install anthropic")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set. Either set it and retry, or run "
            "with --demo to see a recorded trace with no API key needed."
        )

    # The client is just a small wrapper that knows how to talk to
    # api.anthropic.com using your API key (read automatically from
    # the ANTHROPIC_API_KEY environment variable).
    client = anthropic.Anthropic()

    # "messages" is the whole conversation so far. We start it with
    # just the scenario description as if the user typed it in.
    messages = [{"role": "user", "content": SCENARIO_PROMPTS[scenario_key]}]

    # THE LOOP: keep talking to Claude until it stops asking to use tools.
    for _ in range(max_turns):

        # 1. Send everything so far (system prompt + tool menu + full
        #    conversation) to Claude and get its next response.
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )

        # 2. Claude's response can contain plain text (its reasoning,
        #    printed for us to read) AND/OR requests to call tools.
        #    Print any text parts immediately.
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print("\n" + colors.agent_line(block.text))

        # 3. If Claude did NOT ask to use a tool this turn, it means
        #    it's finished — stop the loop.
        if response.stop_reason != "tool_use":
            break

        # 4. Otherwise, add Claude's response to the conversation
        #    history (so it remembers what it just said/asked), then
        #    find every tool it requested and actually run it.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print("\n" + colors.tool_call_line(f"{block.name}({block.input})"))

            # This is the key line: look up the real Python function
            # by name in TOOL_IMPLEMENTATIONS (from tools.py) and run
            # it with the exact arguments Claude provided.
            result = TOOL_IMPLEMENTATIONS[block.name](**block.input)
            print(colors.tool_result_line(result))

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,  # links this result back to Claude's specific request
                "content": result,
            })

        # 5. Feed all the tool results back into the conversation as
        #    if the "user" replied with them, and loop again — Claude
        #    will now see these results and decide what to do next.
        messages.append({"role": "user", "content": tool_results})

    else:
        print("\n[agent]: reached max turns without finishing.")


# =====================================================================
# ENTRY POINT — what runs when you type "python agent.py ..."
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fraud Detection Agent demo")
    parser.add_argument("--demo", action="store_true", help="Run free, no API key needed")
    parser.add_argument("--live", metavar="SCENARIO", choices=SCENARIO_PROMPTS.keys(),
                         help="Run for real against the Claude API (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--no-color", action="store_true",
                         help="Disable colored output (plain text only)")
    args = parser.parse_args()

    if args.no_color:
        colors.disable_color()

    if args.live:
        run_live(args.live)
    else:
        # Default behaviour: run BOTH demo scenarios, free of charge.
        for key in DEMO_SCENARIOS:
            run_demo(key)
