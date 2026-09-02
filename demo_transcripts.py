"""
=====================================================================
 DEMO TRANSCRIPTS — recorded traces for the free --demo mode
=====================================================================
WHAT THIS FILE IS:
Each entry below is a hand-written recording of what a REAL run of
run_live() (in agent.py) produces for that scenario — same tool
calls, same shape of reasoning. It exists so that anyone who clones
this project from GitHub can run `python agent.py --demo` and see
the full agent loop with:
  - no ANTHROPIC_API_KEY needed
  - no cost
  - no network connection needed

HOW EACH TRACE IS STRUCTURED:
Each "trace" is a list of steps. Each step is a tuple where the FIRST
item says what kind of step it is:
  ("text", "some reasoning Claude wrote")
  ("tool_call", "tool_name", {"arg": "value"})
  ("tool_result", "the JSON string the tool would have returned")

agent.py's run_demo() function loops over this list and prints each
step, in order, with a short pause — mimicking watching the real
agent think out loud.
=====================================================================
"""

DEMO_SCENARIOS = {

    # -------------------------------------------------------------
    # SCENARIO 1: Romance scam
    # -------------------------------------------------------------
    # First-time payee + very new online relationship + urgent money
    # request = classic APP (authorised push payment) scam pattern.
    # Expected ending: hold_transaction + clarifying questions
    # (because the USER is the one being deceived here, and can
    # still be reasoned with).
    "romance_scam": {
        "description": (
            "First-time payee, met on a dating app 6 weeks ago, urgent "
            "visa-fee framing — a textbook APP romance scam pattern."
        ),
        "trace": [
            ("text", "I'll start by checking whether this is a known payee for this user."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "Alex Rivera"}),
            ("tool_result", '{"payee_name": "Alex Rivera", "previously_paid": false, "total_known_payees_for_user": 4}'),

            ("text", "First-time payee — that's a risk signal on its own. Let me check this against known fraud typologies."),
            ("tool_call", "check_fraud_patterns", {"context_description": "First payment to new payee, met on dating app 6 weeks ago, urgent visa fee framing, never met in person"}),
            ("tool_result", "{...known_fraud_typologies list including romance_scam...}"),

            ("text",
             "This closely matches the 'romance scam' typology: a first-time payee, a "
             "relationship that started online and is only 6 weeks old, no in-person "
             "meeting, and urgent framing around a visa fee — a very common romance scam "
             "narrative. I'm not certain this is fraud, but the risk signals are strong "
             "enough to warrant a pause before this money is sent."),

            ("tool_call", "hold_transaction", {
                "transaction_id": "txn_001",
                "reason": "First-time payee combined with signals matching a known romance scam pattern (recent online relationship, no in-person meeting, urgent visa-fee framing).",
                "risk_level": "high",
            }),
            ("tool_result", '{"transaction_id": "txn_001", "status": "held", "risk_level": "high", "next_step": "Escalated for secondary review / user confirmation."}'),

            ("text",
             "I've placed a short hold on this payment rather than blocking or sending it. "
             "Before it goes through, it would help to know: Have you met Alex in person? "
             "Has anyone else you know spoken with them? Is there any way to verify the "
             "visa fee request directly with an official source (not a number Alex gave you)? "
             "If you're confident this is legitimate, you can confirm and release the hold."),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 2: Investment / crypto scam
    # -------------------------------------------------------------
    # Repeated payments to the same platform, found via a social media ad,
    # promising guaranteed returns — a classic escalating investment scam.
    "investment_scam": {
        "description": (
            "Third payment in 48 hours to a crypto platform found via an "
            "Instagram ad promising guaranteed 40% returns — an escalating "
            "investment scam pattern."
        ),
        "trace": [
            ("text", "Repeated payment to the same platform in a short window — checking transaction velocity first."),
            ("tool_call", "check_transaction_velocity", {"user_id": "user_123", "window_hours": 48}),
            ("tool_result", '{"user_id": "user_123", "window_hours": 48, "transaction_count_in_window": 3, "elevated": true}'),

            ("text", "Velocity is elevated — three payments in 48 hours. Checking the payee history too."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "CoinSurge Capital"}),
            ("tool_result", '{"payee_name": "CoinSurge Capital", "previously_paid": true, "total_known_payees_for_user": 4}'),

            ("text",
             "This isn't a first-time payee, but repeated, escalating payments to the same "
             "platform — one found via an unsolicited social media ad and promising a "
             "guaranteed 40% return — is itself a strong signal. Let me check this against "
             "known typologies."),
            ("tool_call", "check_fraud_patterns", {"context_description": "Repeated payments to a crypto/investment platform found via social media ad, promising guaranteed high returns, three payments in 48 hours"}),
            ("tool_result", "{...known_fraud_typologies list including app_investment_scam...}"),

            ("text",
             "This matches the investment/crypto scam typology closely: guaranteed high "
             "returns, discovery via an unsolicited ad, and escalating repeat payments are "
             "all textbook signals. Genuine investment platforms don't guarantee returns, "
             "and legitimate ones don't typically need repeated top-ups within 48 hours to "
             "'unlock' anything."),
            ("tool_call", "hold_transaction", {
                "transaction_id": "txn_003",
                "reason": "Escalating repeat payments to a platform found via social media, promising guaranteed high returns — matches investment scam pattern.",
                "risk_level": "high",
            }),
            ("tool_result", '{"transaction_id": "txn_003", "status": "held", "risk_level": "high", "next_step": "Escalated for secondary review / user confirmation."}'),

            ("text",
             "I've held this payment. A few things worth checking before it goes through: "
             "Have you been able to withdraw any funds from this platform before, or only "
             "deposit? Is the 40% return described as 'guaranteed'? Genuine investments "
             "never guarantee returns — that promise alone is a major red flag."),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 3: Bank/official impersonation scam
    # -------------------------------------------------------------
    # A classic and highly damaging pattern: someone claiming to be from
    # the user's own bank convinces them to move their own money to a
    # "safe account". Expected ending: hold + clarifying questions.
    "impersonation_scam": {
        "description": (
            "User was called by someone claiming to be their bank's fraud "
            "team, told to move their full balance to a 'safe account' — "
            "a bank impersonation scam."
        ),
        "trace": [
            ("text", "First checking whether this payee has been paid before."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "Secure Holding Account"}),
            ("tool_result", '{"payee_name": "Secure Holding Account", "previously_paid": false, "total_known_payees_for_user": 4}'),

            ("text",
             "First-time payee, and the story behind it — an unsolicited call claiming to be "
             "the bank's fraud team, urging an urgent transfer to a newly-named 'safe "
             "account', and discouraging the user from hanging up to verify — is a very "
             "well-documented scam script. Checking the typology list to confirm."),
            ("tool_call", "check_fraud_patterns", {"context_description": "Payee contacted user by phone claiming to be bank fraud team, said account was compromised, urged transfer to a new 'safe account', discouraged hanging up to verify independently"}),
            ("tool_result", "{...known_fraud_typologies list including app_impersonation_scam...}"),

            ("text",
             "This matches the bank/official impersonation scam typology almost exactly. "
             "A genuine bank will never ask a customer to move money to a 'safe account' "
             "over the phone, and will never discourage someone from hanging up to verify "
             "independently — that specific combination is one of the strongest scam "
             "indicators there is."),
            ("tool_call", "hold_transaction", {
                "transaction_id": "txn_004",
                "reason": "First-time payee combined with an unsolicited call urging transfer to a 'safe account' and discouraging independent verification — matches bank impersonation scam pattern almost exactly.",
                "risk_level": "high",
            }),
            ("tool_result", '{"transaction_id": "txn_004", "status": "held", "risk_level": "high", "next_step": "Escalated for secondary review / user confirmation."}'),

            ("text",
             "I've held this payment before it can be sent. Please hang up on that call if "
             "it's still ongoing, and call your bank back using the number on your card or "
             "their official app — never the number given to you on the call. Real banks "
             "will never ask you to move money to a 'safe account'."),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 4: Invoice / purchase scam
    # -------------------------------------------------------------
    # A new, unverified seller pushing an off-platform payment method at a
    # below-market price — a purchase scam that costs businesses and
    # individuals alike. Expected ending: hold + clarifying questions.
    "invoice_fraud": {
        "description": (
            "Payment to a new, unverified supplier who pushed a direct bank "
            "transfer instead of platform checkout, at a below-market price "
            "— an invoice/purchase scam pattern."
        ),
        "trace": [
            ("text", "Checking whether this supplier has been paid before."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "Bright Peak Traders"}),
            ("tool_result", '{"payee_name": "Bright Peak Traders", "previously_paid": false, "total_known_payees_for_user": 4}'),

            ("text",
             "First-time payee. The context is worth checking against known typologies: no "
             "reviews or storefront history, insistence on a direct bank transfer instead of "
             "the marketplace's buyer-protected checkout, and a price noticeably below "
             "market rate."),
            ("tool_call", "check_fraud_patterns", {"context_description": "New unverified seller, no reviews, pushed direct bank transfer instead of platform checkout, price below market rate, pressure to pay quickly"}),
            ("tool_result", "{...known_fraud_typologies list including invoice_fraud...}"),

            ("text",
             "This matches the invoice/purchase scam typology: sellers running this scam "
             "typically avoid platforms with buyer protection for exactly this reason, and "
             "an unusually good price is the hook that gets people to skip their usual "
             "caution."),
            ("tool_call", "hold_transaction", {
                "transaction_id": "txn_005",
                "reason": "New, unverified seller pushing direct bank transfer over platform checkout at a below-market price — matches invoice/purchase scam pattern.",
                "risk_level": "medium",
            }),
            ("tool_result", '{"transaction_id": "txn_005", "status": "held", "risk_level": "medium", "next_step": "Escalated for secondary review / user confirmation."}'),

            ("text",
             "I've held this one for a quick check. Does this seller have any reviews or an "
             "established storefront you can see? If possible, it's worth asking whether "
             "they'd accept payment through the platform's standard checkout instead — that "
             "gives you buyer protection a direct bank transfer doesn't."),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 5: Structuring / smurfing
    # -------------------------------------------------------------
    # Several payments, each just under a review threshold, to different
    # new payees in a short window — a pattern designed to avoid detection.
    # Expected ending: hold AND escalate (this is a money-laundering risk
    # pattern across multiple transactions, not a single scam to talk
    # someone out of).
    "structuring": {
        "description": (
            "Four payments just under a review threshold, to four "
            "different new payees, within six hours — a structuring / "
            "money-laundering risk pattern."
        ),
        "trace": [
            ("text", "Several payments to different new payees in a short window — checking transaction velocity first."),
            ("tool_call", "check_transaction_velocity", {"user_id": "user_123", "window_hours": 6}),
            ("tool_result", '{"user_id": "user_123", "window_hours": 6, "transaction_count_in_window": 4, "elevated": true}'),

            ("text", "Velocity is elevated — four payments in six hours. Checking whether the latest payee is a known one."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "Orion Freight Co"}),
            ("tool_result", '{"payee_name": "Orion Freight Co", "previously_paid": false, "total_known_payees_for_user": 4}'),

            ("text",
             "Another first-time payee. Combined with several payments, each just under a "
             "typical review threshold, sent to different new payees in a short window — "
             "this resembles structuring. Checking the typology list to confirm."),
            ("tool_call", "check_fraud_patterns", {"context_description": "Four payments just under a reporting threshold, to four different new payees, within six hours"}),
            ("tool_result", "{...known_fraud_typologies list including structuring...}"),

            ("text",
             "This matches the structuring/smurfing typology: the amounts sitting just under "
             "a threshold, and the spread across several new payees in a short window, is a "
             "pattern that's more about avoiding a single large flagged transaction than "
             "about any one payment looking suspicious on its own. Because this is a "
             "money-laundering risk pattern rather than a scam I can resolve by asking the "
             "user questions, I'm holding this payment and escalating the wider pattern for "
             "a compliance review."),
            ("tool_call", "hold_transaction", {
                "transaction_id": "txn_006",
                "reason": "Four payments just under a review threshold to different new payees within six hours — matches structuring pattern.",
                "risk_level": "high",
            }),
            ("tool_result", '{"transaction_id": "txn_006", "status": "held", "risk_level": "high", "next_step": "Escalated for secondary review / user confirmation."}'),
            ("tool_call", "escalate_to_human", {
                "transaction_id": "txn_006",
                "summary": "Pattern of 4 payments just under review threshold to different new payees within 6 hours. Matches structuring typology. Recommend compliance review of the account's recent activity as a whole, not just this single transaction.",
            }),
            ("tool_result", '{"transaction_id": "txn_006", "status": "escalated_to_human"}'),

            ("text",
             "This account's recent activity has been flagged for a compliance review, "
             "since the pattern spans several transactions rather than being about this "
             "payment alone. A specialist will follow up."),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 6: Card-not-present fraud
    # -------------------------------------------------------------
    # Small "test" transactions followed by a large purchase in an
    # unfamiliar country — a classic stolen-card-details pattern. Expected
    # ending: escalate to human (this is unauthorised fraud, i.e. the card
    # itself may be compromised, not the cardholder being deceived).
    "card_not_present": {
        "description": (
            "Two small test transactions followed by a large purchase in a "
            "country the card has never been used in — a card-not-present "
            "fraud pattern."
        ),
        "trace": [
            ("text", "Unusual card activity — checking recent card transactions for a test-transaction pattern."),
            ("tool_call", "check_card_activity", {"user_id": "user_123"}),
            ("tool_result", '{"test_transaction_pattern_detected": true, "small_test_transaction_count": 2, "latest_transaction_amount_gbp": 650, "latest_transaction_country": "NG", "usual_country": "GB", "country_mismatch": true}'),

            ("text",
             "This matches a card-not-present fraud pattern closely: two small transactions "
             "(the kind fraudsters use to check a stolen card still works) followed "
             "immediately by a large purchase, in a country that doesn't match the "
             "cardholder's usual activity. Checking the typology list to confirm."),
            ("tool_call", "check_fraud_patterns", {"context_description": "Two small test transactions followed by a large purchase, country mismatch from cardholder's usual activity"}),
            ("tool_result", "{...known_fraud_typologies list including card_not_present...}"),

            ("text",
             "This is unauthorised fraud rather than a scam the cardholder is being talked "
             "into — the card details themselves may be compromised. Since the person using "
             "the card right now may not be the genuine cardholder, asking clarifying "
             "questions isn't the right move here. This should go straight to a human "
             "analyst, with a recommendation to freeze the card."),
            ("tool_call", "escalate_to_human", {
                "transaction_id": "txn_007",
                "summary": "Test-transaction pattern (2 small charges) followed by a 650 GBP purchase in a country never used before by this card. Matches card-not-present fraud typology. Recommend immediate card freeze and reissue.",
            }),
            ("tool_result", '{"transaction_id": "txn_007", "status": "escalated_to_human"}'),
        ],
    },

    # -------------------------------------------------------------
    # SCENARIO 7: Account takeover
    # -------------------------------------------------------------
    # Unrecognised login (new country + new device) followed
    # IMMEDIATELY by a large first-time payment. Expected ending:
    # escalate_to_human, NOT clarifying questions — because if the
    # account is genuinely compromised, whoever is "answering" the
    # agent's questions might be the attacker, not the real user.
    # This contrast with scenario 1 is the core design idea of the
    # whole project — see the system prompt in agent.py.
    "account_takeover": {
        "description": (
            "Login from an unrecognised country and device, immediately "
            "followed by a large first-time payment — classic account "
            "takeover pattern."
        ),
        "trace": [
            ("text", "Large first-time payment right after login — I'll check the login pattern first."),
            ("tool_call", "check_login_anomaly", {"user_id": "user_123"}),
            ("tool_result", '{"latest_login_country": "VN", "usual_country": "GB", "latest_login_device": "device_x9", "device_recognised": false, "anomaly_detected": true}'),

            ("text", "Anomaly confirmed: unfamiliar country and an unrecognised device. Now checking the payee."),
            ("tool_call", "get_payee_history", {"user_id": "user_123", "payee_name": "Quicksilver Holdings"}),
            ("tool_result", '{"payee_name": "Quicksilver Holdings", "previously_paid": false, "total_known_payees_for_user": 4}'),

            ("text", "First-time payee too. Checking this combination against known typologies."),
            ("tool_call", "check_fraud_patterns", {"context_description": "Login from unrecognised country/device, immediately followed by large first-time payment"}),
            ("tool_result", "{...known_fraud_typologies list including account_takeover...}"),

            ("text",
             "This matches the account takeover pattern closely: an unrecognised device and "
             "country, followed almost immediately by a large payment to a brand-new payee. "
             "This is higher-confidence risk than a typical scam case because it suggests the "
             "account itself may be compromised, not just a user being deceived. I'm escalating "
             "this to a human analyst rather than resolving it with clarifying questions, since "
             "if the account is compromised, the person on the other end of this chat may not "
             "be the genuine account holder."),

            ("tool_call", "escalate_to_human", {
                "transaction_id": "txn_002",
                "summary": "Unrecognised device/country login immediately followed by large first-time payment. Matches account takeover pattern. Recommend identity re-verification before any further action.",
            }),
            ("tool_result", '{"transaction_id": "txn_002", "status": "escalated_to_human"}'),
        ],
    },
}
