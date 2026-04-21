from generator_dataset.posting_engine import post_all_transactions
from generator_dataset.main import build_phase5
from generator_dataset.validations import validate_phase6


def test_posting_engine_posts_phase5_transactions() -> None:
    context = build_phase5()

    opening_gl_count = len(context.tables["GLEntry"])
    post_all_transactions(context)
    results = validate_phase6(context)
    accounts = (
        context.tables["Account"]
        .assign(AccountNumber=context.tables["Account"]["AccountNumber"].astype(str))
        .set_index("AccountNumber")["AccountID"]
        .astype(int)
        .to_dict()
    )
    gl = context.tables["GLEntry"]
    freight_revenue_rows = gl[gl["AccountID"].astype(int).eq(accounts["4050"])]
    freight_expense_rows = gl[gl["AccountID"].astype(int).eq(accounts["5050"])]

    assert results["exceptions"] == []
    assert len(context.tables["GLEntry"]) > opening_gl_count
    assert results["gl_balance"]["exception_count"] == 0
    assert results["trial_balance_difference"] == 0
    assert results["account_rollforward"]["exception_count"] == 0
    assert round(float(freight_revenue_rows["Credit"].sum()) - float(freight_revenue_rows["Debit"].sum()), 2) > 0
    assert round(float(freight_expense_rows["Debit"].sum()) - float(freight_expense_rows["Credit"].sum()), 2) > 0
