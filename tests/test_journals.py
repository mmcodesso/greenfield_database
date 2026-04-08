from dataclasses import replace

from greenfield_dataset.anomalies import inject_anomalies
from greenfield_dataset.journals import generate_recurring_manual_journals, generate_year_end_close_journals
from greenfield_dataset.main import build_phase5
from greenfield_dataset.posting_engine import post_all_transactions
from greenfield_dataset.validations import validate_phase8, validate_phase9


def test_generate_recurring_manual_journals_counts_and_links() -> None:
    context = build_phase5()

    generate_recurring_manual_journals(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    assert int(entry_type_counts["Opening"]) == 1
    assert int(entry_type_counts["Payroll Accrual"]) == 480
    assert int(entry_type_counts["Payroll Settlement"]) == 472
    assert int(entry_type_counts["Rent"]) == 120
    assert int(entry_type_counts["Utilities"]) == 60
    assert int(entry_type_counts["Depreciation"]) == 180
    assert int(entry_type_counts["Accrual"]) == 60
    assert int(entry_type_counts["Accrual Reversal"]) == 59
    assert len(context.tables["JournalEntry"]) == 1432

    reversals = context.tables["JournalEntry"][context.tables["JournalEntry"]["EntryType"].eq("Accrual Reversal")]
    assert reversals["ReversesJournalEntryID"].notna().all()
    assert context.tables["GLEntry"]["VoucherType"].eq("JournalEntry").all()
    assert 2000 <= len(context.tables["Budget"]) <= 4500


def test_generate_year_end_close_journals_clean_phase9_validation() -> None:
    context = build_phase5()
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    results = validate_phase9(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    assert int(entry_type_counts["Year-End Close - P&L to Income Summary"]) == 5
    assert int(entry_type_counts["Year-End Close - Income Summary to Retained Earnings"]) == 5
    assert len(context.tables["JournalEntry"]) == 1442
    assert results["exceptions"] == []
    assert results["gl_balance"]["exception_count"] == 0
    assert results["trial_balance_difference"] == 0
    assert results["journal_controls"]["exception_count"] == 0
    assert results["p2p_controls"]["exception_count"] == 0


def test_phase8_journal_anomalies_preserve_gl_balance() -> None:
    context = build_phase5()

    generate_recurring_manual_journals(context)
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
