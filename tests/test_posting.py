from CharlesRiver_dataset.posting_engine import post_all_transactions
from CharlesRiver_dataset.main import build_phase5
from CharlesRiver_dataset.validations import validate_phase6


def test_posting_engine_posts_phase5_transactions() -> None:
    context = build_phase5()

    opening_gl_count = len(context.tables["GLEntry"])
    post_all_transactions(context)
    results = validate_phase6(context)

    assert results["exceptions"] == []
    assert len(context.tables["GLEntry"]) > opening_gl_count
    assert results["gl_balance"]["exception_count"] == 0
    assert results["trial_balance_difference"] == 0
    assert results["account_rollforward"]["exception_count"] == 0
