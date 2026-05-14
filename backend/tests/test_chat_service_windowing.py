from datetime import datetime, timezone

from services.chat_service import build_system_prompt, compute_confidence, resolve_context_window


def test_resolve_context_window_falls_back_to_latest_available_period_for_stale_data():
    latest = datetime(2024, 11, 27, tzinfo=timezone.utc)
    now = datetime(2026, 5, 14, tzinfo=timezone.utc)

    cutoff, window_end, stale_days = resolve_context_window(latest, now=now)

    assert cutoff.date().isoformat() == "2024-08-29"
    assert window_end.date().isoformat() == "2024-11-27"
    assert stale_days > 365


def test_compute_confidence_downgrades_stale_data_even_with_many_transactions():
    level, note = compute_confidence({
        "txn_count": 580,
        "months_of_data": 3,
        "window_end": "2024-11-27",
        "stale_days": 533,
    })

    assert level == "low"
    assert "2024-11-27" in note
    assert "historical" in note.lower()


def test_build_system_prompt_mentions_exact_data_window_for_grounding():
    prompt = build_system_prompt(
        context="Top Expense Categories (2024-08-29 to 2024-11-27):\n  - Payroll: INR 1,000.00",
        confidence_level="low",
        confidence_note="Data confidence: LOW — stale but usable historically.",
        metadata={
            "txn_count": 580,
            "months_of_data": 3,
            "intents": ["category_spend"],
            "rag_matches": 0,
            "window_start": "2024-08-29",
            "window_end": "2024-11-27",
            "stale_days": 533,
        },
    )

    assert "DATA WINDOW: 2024-08-29 to 2024-11-27" in prompt
    assert "RECENCY WARNING" in prompt
    assert "Recommendations:" in prompt
    assert "plain text" in prompt
