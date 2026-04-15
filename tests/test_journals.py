from dataclasses import replace

from generator_dataset.anomalies import inject_anomalies
from generator_dataset.journals import (
    generate_accrual_adjustment_journals,
    generate_recurring_manual_journals,
    generate_year_end_close_journals,
)
from generator_dataset.main import build_phase5
from generator_dataset.p2p import generate_accrued_service_settlements
from generator_dataset.posting_engine import post_all_transactions
from generator_dataset.validations import validate_phase8, validate_phase13


def test_generate_recurring_manual_journals_counts_and_links() -> None:
    context = build_phase5()

    generate_recurring_manual_journals(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    fiscal_month_count = 60

    assert int(entry_type_counts["Opening"]) == 1
    assert int(entry_type_counts["Rent"]) == fiscal_month_count * 2
    assert int(entry_type_counts["Utilities"]) == fiscal_month_count
    assert int(entry_type_counts["Depreciation"]) == fiscal_month_count * 3
    assert int(entry_type_counts["Accrual"]) == fiscal_month_count * 3
    assert int(entry_type_counts.get("Accrual Reversal", 0)) == 0
    assert len(context.tables["JournalEntry"]) == sum(int(count) for count in entry_type_counts.values())

    adjustments = context.tables["JournalEntry"][context.tables["JournalEntry"]["EntryType"].eq("Accrual Adjustment")]
    if not adjustments.empty:
        assert adjustments["ReversesJournalEntryID"].notna().all()
    assert context.tables["GLEntry"]["VoucherType"].eq("JournalEntry").all()
    assert 2000 <= len(context.tables["Budget"]) <= 4500


def test_generate_year_end_close_journals_clean_phase12_validation() -> None:
    context = build_phase5()
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    results = validate_phase13(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    assert int(entry_type_counts["Year-End Close - P&L to Income Summary"]) == 5
    assert int(entry_type_counts["Year-End Close - Income Summary to Retained Earnings"]) == 5
    assert len(context.tables["JournalEntry"]) == sum(int(count) for count in entry_type_counts.values())
    assert results["exceptions"] == []
    assert results["gl_balance"]["exception_count"] == 0
    assert results["trial_balance_difference"] == 0
    assert results["journal_controls"]["exception_count"] == 0
    assert results["p2p_controls"]["exception_count"] == 0
    assert results["manufacturing_controls"]["exception_count"] == 0
    assert results["payroll_controls"]["exception_count"] == 0

    gl = context.tables["GLEntry"]
    accounts = (
        context.tables["Account"]
        .assign(AccountNumber=context.tables["Account"]["AccountNumber"].astype(str))
        .set_index("AccountNumber")["AccountID"]
        .astype(int)
        .to_dict()
    )
    for account_number in ["6100", "6140", "6180"]:
        account_id = accounts[account_number]
        account_rows = gl[gl["AccountID"].astype(int).eq(account_id)]
        assert round(float(account_rows["Debit"].sum()), 2) > 0
        assert round(float(account_rows["Credit"].sum()), 2) > 0


def test_accrued_expense_settlement_uses_purchase_invoice_path() -> None:
    context = build_phase5()
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    results = validate_phase13(context)

    service_lines = context.tables["PurchaseInvoiceLine"][
        context.tables["PurchaseInvoiceLine"]["AccrualJournalEntryID"].notna()
    ].copy()
    assert not service_lines.empty
    assert service_lines["GoodsReceiptLineID"].isna().all()
    assert service_lines["POLineID"].isna().all()
    assert context.tables["DisbursementPayment"]["PurchaseInvoiceID"].astype(int).isin(
        service_lines["PurchaseInvoiceID"].astype(int)
    ).any()
    assert results["exceptions"] == []
    assert results["account_rollforward"]["exception_count"] == 0


def test_phase8_journal_anomalies_preserve_gl_balance() -> None:
    context = build_phase5()

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    inject_anomalies(context)
    results = validate_phase8(context)

    anomaly_types = {entry["anomaly_type"] for entry in context.anomaly_log}
    weekend_years = {
        entry["fiscal_year"]
        for entry in context.anomaly_log
        if entry["anomaly_type"] == "weekend_journal_entry"
    }

    assert results["anomaly_count"] > 0
    assert results["gl_balance"]["exception_count"] == 0
    assert results["trial_balance_difference"] == 0
    assert results["journal_controls"]["exception_count"] > 0
    assert len(weekend_years) > 1
    assert "same_creator_approver_journal" in anomaly_types
    assert "missing_reversal_link" in anomaly_types
    assert "late_reversal" in anomaly_types
    assert "round_dollar_manual_journal" in anomaly_types
