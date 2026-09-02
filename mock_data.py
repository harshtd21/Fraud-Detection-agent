"""
=====================================================================
 MOCK DATA LAYER
=====================================================================
WHAT THIS FILE IS:
This file is a fake, hand-written stand-in for a real bank's database.
None of this data is real — it was invented so the agent has something
realistic to look up and reason over.

WHY IT EXISTS SEPARATELY:
In a real fintech company, this data would come from live systems:
  - payee history      -> a payments database
  - login history       -> a device-fingerprinting / auth service
  - fraud typologies    -> a fraud-intelligence platform, updated by
                           analysts and possibly RAG-retrieved from
                           real case data
By keeping it in its own file as plain Python dictionaries, the rest
of the code (tools.py, agent.py) doesn't care whether this data comes
from a dictionary or a real API call later — that's the point of
separating "data" from "logic".
=====================================================================
"""

# ---------------------------------------------------------------------------
# STEP 1: Payee history
# ---------------------------------------------------------------------------
# This says: "user_123 has previously paid these 4 people/companies before."
# Why it matters: a payment to someone NOT in this list is a classic fraud
# signal — first-time payees are riskier than payees you've paid 10 times.
KNOWN_PAYEES = {
    "user_123": ["Landlord Ltd", "Mum", "Netflix", "British Gas"],
}


# ---------------------------------------------------------------------------
# STEP 2: Login history (used to detect account takeover)
# ---------------------------------------------------------------------------
# "usual_country" / "usual_device_ids" = the user's normal pattern.
# "recent_logins" = what actually just happened.
# If a login comes from a new country AND a new device, that's a strong
# signal the account may have been broken into by someone else.
LOGIN_HISTORY = {
    "user_123": {
        "usual_country": "GB",
        "usual_device_ids": ["device_a1"],
        "recent_logins": [
            {"country": "GB", "device_id": "device_a1", "hours_ago": 240},
        ],
    },
}


# ---------------------------------------------------------------------------
# STEP 3: Recent transactions (used to detect velocity / structuring)
# ---------------------------------------------------------------------------
# "structuring" = splitting money into several smaller payments to avoid
# detection thresholds. To catch that, you need to look at PATTERNS across
# multiple transactions, not just one payment in isolation — that's why
# this exists as its own list rather than being folded into KNOWN_PAYEES.
RECENT_TRANSACTIONS = {
    "user_123": [
        {"payee": "Landlord Ltd", "amount_gbp": 900, "hours_ago": 700},
    ],
}


# ---------------------------------------------------------------------------
# STEP 3b: Card activity (used to detect card-not-present fraud)
# ---------------------------------------------------------------------------
# Card fraudsters often run one or two tiny "test" transactions first, to
# check a stolen card still works, before attempting one large purchase.
# A large purchase from a country that doesn't match the cardholder's usual
# activity is another strong signal.
CARD_ACTIVITY = {
    "user_123": {
        "usual_country": "GB",
        "recent_card_transactions": [
            {"amount_gbp": 1, "merchant": "Test Merchant A", "country": "GB", "hours_ago": 2},
            {"amount_gbp": 2, "merchant": "Test Merchant B", "country": "GB", "hours_ago": 1.5},
            {"amount_gbp": 650, "merchant": "Electronics Superstore", "country": "NG", "hours_ago": 1},
        ],
    },
}


# ---------------------------------------------------------------------------
# STEP 4: The fraud "knowledge base"
# ---------------------------------------------------------------------------
# This is the most important piece of data in the whole project. It's a
# list of known fraud typologies, each with a "category" (which determines
# HOW the agent should respond — see agent.py's system prompt) and a list
# of "signals" (real-world clues that suggest this typology).
#
# The agent's job (in agent.py) is essentially: take a real scenario,
# compare it against this list, and reason about which entry (if any) it
# matches. This is a simple stand-in for what a proper RAG/vector-search
# system would do once this list grows beyond a handful of typologies —
# see the README for that extension idea.
FRAUD_PATTERNS = [
    {
        "id": "app_romance_scam",
        "category": "Authorised push payment (APP) scam",  # -> user is being deceived, so: HOLD + ask questions
        "name": "Romance scam",
        "signals": [
            "payee met online / on a dating app",
            "relationship is recent (weeks to a few months)",
            "never met in person",
            "urgent personal emergency framing (medical bill, travel, visa fee)",
            "requests for secrecy from friends/family",
        ],
    },
    {
        "id": "app_investment_scam",
        "category": "Authorised push payment (APP) scam",
        "name": "Investment / crypto scam",
        "signals": [
            "promise of unusually high or guaranteed returns",
            "pressure to act before an 'opportunity closes'",
            "found via social media ad or unsolicited message",
            "escalating repeated payments to the same platform",
        ],
    },
    {
        "id": "app_impersonation_scam",
        "category": "Authorised push payment (APP) scam",
        "name": "Bank/police/official impersonation scam",
        "signals": [
            "contacted by phone/text claiming to be bank, police, or government",
            "told account is compromised, funds must move to a 'safe account'",
            "discouraged from hanging up and verifying independently",
            "high urgency, fear-based framing",
        ],
    },
    {
        "id": "invoice_fraud",
        "category": "Authorised push payment (APP) scam",
        "name": "Invoice / purchase scam",
        "signals": [
            "payment for goods/services from a new or unverified seller",
            "seller pushed bank transfer instead of platform checkout",
            "price seems below market, high pressure to pay immediately",
            "little or no seller history/reviews",
        ],
    },
    {
        "id": "account_takeover",
        "category": "Unauthorised fraud",  # -> account may be compromised, so: ESCALATE to a human, don't interrogate
        "name": "Account takeover",
        "signals": [
            "login from an unfamiliar country or device",
            "login shortly followed by a large or first-time payment",
            "password/security details changed shortly before payment",
            "user's usual device/location pattern is broken",
        ],
    },
    {
        "id": "card_not_present",
        "category": "Unauthorised fraud",
        "name": "Card-not-present / stolen card details fraud",
        "signals": [
            "multiple small test transactions followed by one large one",
            "transaction location inconsistent with cardholder's recent activity",
            "new merchant category never used before by this card",
        ],
    },
    {
        "id": "structuring",
        "category": "Money laundering risk",
        "name": "Structuring / smurfing",
        "signals": [
            "multiple payments just under a reporting/review threshold",
            "rapid succession of transfers to different new payees",
            "pattern designed to avoid a single large flagged transaction",
        ],
    },
]


# ---------------------------------------------------------------------------
# STEP 5: A small helper function
# ---------------------------------------------------------------------------
# This is plain Python logic (not "AI" at all) that counts how many
# transactions a user made within a given time window. tools.py calls
# this and hands the result to Claude — Claude never touches this raw
# data directly, it only ever sees the JSON that tools.py returns.
def get_recent_transaction_count(user_id: str, hours: int = 24) -> int:
    txns = RECENT_TRANSACTIONS.get(user_id, [])
    return sum(1 for t in txns if t["hours_ago"] <= hours)
