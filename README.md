FRAUD DETECTION AGENT (Claude API)
===================================

A Claude-powered agent that reasons over payment and login context to
decide whether a transaction should be released, held for clarification,
or escalated to a human analyst -- covering multiple fraud typologies,
not just a single rule.

No API key needed to see it work. Run:

    python agent.py --demo

for a full, realistic trace of the agent's reasoning and tool calls,
across 7 fraud scenarios, recorded from real runs, at zero cost. Output
is color-coded (agent reasoning in cyan, tool calls in yellow, tool
results in green) so it's easy to follow even if you've never read
agent code before.


WHY THIS PROJECT
-----------------

Fraud tooling in most demos flags a single "is this fraudulent, yes/no"
signal. Real fraud review is more nuanced than that, and the response
should differ by fraud type:

  - Authorised push payment (APP) scams
    (romance, investment, impersonation, invoice fraud)
    The user is being deceived into sending money themselves.
    Right move: hold + a few calm clarifying questions, not a block.

  - Unauthorised fraud
    (account takeover, card-not-present fraud)
    The account or card may be compromised.
    Right move: escalate to a human, since the person in the chat may
    not be the genuine account holder.

  - Structuring / money-laundering risk
    Patterns across multiple transactions, not one.

This agent's system prompt explicitly reasons about which category a
scenario falls into, because that changes what "the right response"
even is -- that distinction is the actual design decision this project
demonstrates.


FRAUD SCENARIOS COVERED (7 TOTAL)
-----------------------------------

  Scenario                            Category                Agent action
  ----------------------------------------------------------------------------
  Romance scam                        APP scam                Hold + questions
  Investment / crypto scam            APP scam                Hold + questions
  Bank/official impersonation scam    APP scam                Hold + questions
  Invoice / purchase scam             APP scam                Hold + questions
  Structuring / smurfing              Money laundering risk   Hold + escalate
  Card-not-present fraud              Unauthorised fraud      Escalate
  Account takeover                    Unauthorised fraud      Escalate


HOW IT WORKS
-------------

  mock_data.py          Simulated payee history, login history, card
                         activity, transaction history, and a
                         fraud-typology knowledge base

  tools.py               Tool implementations (get_payee_history,
                         check_login_anomaly, check_transaction_velocity,
                         check_card_activity, check_fraud_patterns,
                         hold_transaction, release_transaction,
                         escalate_to_human)

  agent.py               System prompt + tool schemas + the agent loop

  demo_transcripts.py    Pre-recorded traces used by --demo mode
                         (7 scenarios)

  colors.py              Terminal color-coding, no external dependencies

The loop follows the standard Claude tool-use pattern: send messages
with tool definitions, Claude requests a tool_use, execute it, feed
the result back in, repeat until Claude stops calling tools and gives
a final answer.


RUNNING IT
-----------

Free / no API key (recommended for browsing this repo):

    python agent.py --demo

This replays all 7 scenarios in the table above, showing every
reasoning step and tool call, with no network calls made and no
dependencies to install. Add --no-color for plain text output.

Live, against the real Claude API (optional, uses a small amount of
API credit):

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here
    python agent.py --live romance_scam

Other --live scenario names:
    investment_scam, impersonation_scam, invoice_fraud, structuring,
    card_not_present, account_takeover


EXTENDING THIS
---------------

  - Swap check_fraud_patterns's static list for real vector-search RAG
    once the typology library grows past a handful of patterns

  - Add structured audit logging of every decision + reasoning trace --
    the detail that matters most for a regulated fintech context

  - Wrap in a FastAPI endpoint to sit in front of a real payment flow

  - Add a confidence-calibration step: ask the agent to output a
    numeric risk score alongside its qualitative reasoning, for
    downstream thresholding


NOT INCLUDED (BY DESIGN)
--------------------------

This is a portfolio/learning project, not production fraud
infrastructure -- it uses mock data, has no real payment integration,
and is not a substitute for regulated fraud-detection systems.


BACKGROUND READING
--------------------

  - Building effective agents (Anthropic)
    https://www.anthropic.com/engineering/building-effective-agents

  - Writing effective tools for agents (Anthropic)
    https://www.anthropic.com/engineering/writing-tools-for-agents
