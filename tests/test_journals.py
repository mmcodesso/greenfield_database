from dataclasses import replace

import pytest

from generator_dataset.accrual_catalog import ACCRUAL_ACCOUNT_METADATA
from generator_dataset.fixed_assets import fixed_asset_opening_profiles
from generator_dataset.anomalies import inject_anomalies
from generator_dataset.journals import (
    first_business_day_on_or_after,
    fiscal_months,
    generate_accrual_adjustment_journals,
    generate_recurring_manual_journals,
    generate_year_end_close_journals,
)
from generator_dataset.main import build_phase5
from generator_dataset.p2p import generate_accrued_service_settlements
from generator_dataset.posting_engine import post_all_transactions
from generator_dataset.validations import validate_phase8, validate_phase13


def _accrual_journal_row(context, entry_number: str):
    matches = context.tables["JournalEntry"].loc[context.tables["JournalEntry"]["EntryNumber"].eq(entry_number)]
    assert len(matches) == 1
    return matches.iloc[0]


def _linked_service_invoice_line(context, accrual_journal_id: int):
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    linked_lines = invoice_lines.loc[invoice_lines["AccrualJournalEntryID"].notna()].copy()
    matches = linked_lines.loc[linked_lines["AccrualJournalEntryID"].astype(int).eq(int(accrual_journal_id))]
    assert not matches.empty
    return matches.sort_values("PILineID").iloc[0]


def _find_linked_accrual(context, *, comparison: str):
    accruals = context.tables["JournalEntry"].loc[
        context.tables["JournalEntry"]["EntryType"].eq("Accrual"),
        ["JournalEntryID", "EntryNumber", "TotalAmount"],
    ].copy()
    accrual_lookup = {
        int(row["JournalEntryID"]): row
        for row in accruals.to_dict("records")
    }
    linked_lines = context.tables["PurchaseInvoiceLine"].loc[
        context.tables["PurchaseInvoiceLine"]["AccrualJournalEntryID"].notna()
    ].sort_values("PILineID")
    for line in linked_lines.itertuples(index=False):
        accrual = accrual_lookup[int(line.AccrualJournalEntryID)]
        line_total = round(float(line.LineTotal), 2)
        accrual_total = round(float(accrual["TotalAmount"]), 2)
        if comparison == "under" and line_total < accrual_total:
            return accrual, line._asdict()
        if comparison == "over" and line_total > accrual_total:
            return accrual, line._asdict()
    raise AssertionError(f"Missing linked accrual with comparison={comparison}")


def _sync_linked_invoice_amount(context, accrual_entry_number: str, amount: float) -> None:
    accrual = _accrual_journal_row(context, accrual_entry_number)
    invoice_line = _linked_service_invoice_line(context, int(accrual["JournalEntryID"]))
    line_mask = context.tables["PurchaseInvoiceLine"]["PILineID"].astype(int).eq(int(invoice_line["PILineID"]))
    context.tables["PurchaseInvoiceLine"].loc[line_mask, "UnitCost"] = amount
    context.tables["PurchaseInvoiceLine"].loc[line_mask, "LineTotal"] = amount

    invoice_mask = context.tables["PurchaseInvoice"]["PurchaseInvoiceID"].astype(int).eq(int(invoice_line["PurchaseInvoiceID"]))
    context.tables["PurchaseInvoice"].loc[invoice_mask, "SubTotal"] = amount
    context.tables["PurchaseInvoice"].loc[invoice_mask, "GrandTotal"] = amount

    payment_mask = context.tables["DisbursementPayment"]["PurchaseInvoiceID"].astype(int).eq(int(invoice_line["PurchaseInvoiceID"]))
    context.tables["DisbursementPayment"].loc[payment_mask, "Amount"] = amount


def _account_id_by_number(context, account_number: str) -> int:
    matches = context.tables["Account"].loc[context.tables["Account"]["AccountNumber"].astype(str).eq(account_number), "AccountID"]
    assert len(matches) == 1
    return int(matches.iloc[0])


def _accrual_expense_account_number(context, accrual_journal_id: int) -> str:
    gl_rows = context.tables["GLEntry"].loc[
        context.tables["GLEntry"]["SourceDocumentType"].eq("JournalEntry")
        & context.tables["GLEntry"]["SourceDocumentID"].astype(int).eq(int(accrual_journal_id))
        & context.tables["GLEntry"]["Debit"].astype(float).gt(0)
    ]
    account_ids = gl_rows["AccountID"].astype(int).tolist()
    account_map = (
        context.tables["Account"]
        .assign(AccountNumber=context.tables["Account"]["AccountNumber"].astype(str))
        .set_index("AccountID")["AccountNumber"]
        .to_dict()
    )
    for account_id in account_ids:
        account_number = account_map[int(account_id)]
        if account_number != "2040":
            return str(account_number)
    raise AssertionError(f"Missing expense account for accrual journal {accrual_journal_id}")


@pytest.fixture(scope="module")
def phase5_base_context():
    return build_phase5()


@pytest.fixture
def phase5_context(clone_generation_context, phase5_base_context):
    return clone_generation_context(phase5_base_context)


def test_generate_recurring_manual_journals_counts_and_links(phase5_context) -> None:
    context = phase5_context

    generate_recurring_manual_journals(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    fiscal_month_count = len(fiscal_months(context))

    assert int(entry_type_counts["Opening"]) == 1
    assert int(entry_type_counts["Rent"]) == fiscal_month_count * 2
    assert int(entry_type_counts["Utilities"]) == fiscal_month_count
    assert int(entry_type_counts["Depreciation"]) == fiscal_month_count * 3
    assert int(entry_type_counts["Accrual"]) == fiscal_month_count * len(ACCRUAL_ACCOUNT_METADATA)
    assert int(entry_type_counts.get("Accrual Reversal", 0)) == 0
    assert len(context.tables["JournalEntry"]) == sum(int(count) for count in entry_type_counts.values())

    adjustments = context.tables["JournalEntry"][context.tables["JournalEntry"]["EntryType"].eq("Accrual Adjustment")]
    if not adjustments.empty:
        assert adjustments["ReversesJournalEntryID"].notna().all()
    assert context.tables["GLEntry"]["VoucherType"].eq("JournalEntry").all()
    assert 2000 <= len(context.tables["Budget"]) <= 4500


def test_generate_year_end_close_journals_clean_phase12_validation(phase5_context) -> None:
    context = phase5_context
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    results = validate_phase13(context)

    entry_type_counts = context.tables["JournalEntry"]["EntryType"].value_counts().to_dict()
    fiscal_year_count = len({year for year, _ in fiscal_months(context)})
    assert int(entry_type_counts["Year-End Close - P&L to Income Summary"]) == fiscal_year_count
    assert int(entry_type_counts["Year-End Close - Income Summary to Retained Earnings"]) == fiscal_year_count
    assert len(context.tables["JournalEntry"]) == sum(int(count) for count in entry_type_counts.values())
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
    for account_number in ACCRUAL_ACCOUNT_METADATA:
        account_id = accounts[account_number]
        account_rows = gl[gl["AccountID"].astype(int).eq(account_id)]
        assert round(float(account_rows["Debit"].sum()), 2) > 0
        assert round(float(account_rows["Credit"].sum()), 2) > 0


def test_fixed_assets_and_accumulated_depreciation_remain_realistic_over_five_years(phase5_context) -> None:
    context = phase5_context
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)

    accounts = (
        context.tables["Account"]
        .assign(AccountNumber=context.tables["Account"]["AccountNumber"].astype(str))
        .set_index("AccountNumber")["AccountID"]
        .astype(int)
        .to_dict()
    )
    gl = context.tables["GLEntry"]

    for profile in fixed_asset_opening_profiles().values():
        gross_account_id = accounts[profile.asset_account_number]
        gross_rows = gl[gl["AccountID"].astype(int).eq(gross_account_id)]
        gross_balance = round(float(gross_rows["Debit"].astype(float).sum()) - float(gross_rows["Credit"].astype(float).sum()), 2)
        assert gross_balance == round(float(profile.gross_opening_balance), 2)
        if not profile.accumulated_depreciation_account_number:
            continue
        accumulated_account_id = accounts[profile.accumulated_depreciation_account_number]
        accumulated_rows = gl[gl["AccountID"].astype(int).eq(accumulated_account_id)]
        accumulated_balance = round(float(accumulated_rows["Credit"].astype(float).sum()) - float(accumulated_rows["Debit"].astype(float).sum()), 2)
        assert accumulated_balance <= gross_balance + 0.01
        assert round(gross_balance - accumulated_balance, 2) >= -0.01


def test_accrued_expense_settlement_uses_purchase_invoice_path(phase5_context) -> None:
    context = phase5_context
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
    assert results["journal_controls"]["exception_count"] == 0
    assert results["p2p_controls"]["exception_count"] == 0
    assert results["account_rollforward"]["exception_count"] == 0


def test_invoice_linked_under_accrual_creates_exact_full_settlement_adjustment(phase5_context) -> None:
    context = phase5_context
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)

    accrual, invoice_line = _find_linked_accrual(context, comparison="under")
    invoice = context.tables["PurchaseInvoice"].loc[
        context.tables["PurchaseInvoice"]["PurchaseInvoiceID"].astype(int).eq(int(invoice_line["PurchaseInvoiceID"]))
    ].iloc[0]
    adjustments = context.tables["JournalEntry"].loc[
        context.tables["JournalEntry"]["EntryType"].eq("Accrual Adjustment")
        & context.tables["JournalEntry"]["ReversesJournalEntryID"].notna()
    ]
    adjustments = adjustments.loc[adjustments["ReversesJournalEntryID"].astype(int).eq(int(accrual["JournalEntryID"]))]

    assert len(adjustments) == 1
    adjustment = adjustments.iloc[0]
    expected_residual = round(float(accrual["TotalAmount"]) - float(invoice_line["LineTotal"]), 2)
    expense_account_number = _accrual_expense_account_number(context, int(accrual["JournalEntryID"]))
    assert round(float(adjustment["TotalAmount"]), 2) == expected_residual
    assert adjustment["PostingDate"] == first_business_day_on_or_after(str(invoice["ApprovedDate"])).strftime("%Y-%m-%d")

    adjustment_gl = context.tables["GLEntry"].loc[
        context.tables["GLEntry"]["SourceDocumentType"].eq("JournalEntry")
        & context.tables["GLEntry"]["SourceDocumentID"].astype(int).eq(int(adjustment["JournalEntryID"]))
    ]
    debit_2040 = adjustment_gl.loc[
        adjustment_gl["AccountID"].astype(int).eq(_account_id_by_number(context, "2040")),
        "Debit",
    ].sum()
    credit_expense = adjustment_gl.loc[
        adjustment_gl["AccountID"].astype(int).eq(_account_id_by_number(context, expense_account_number)),
        "Credit",
    ].sum()
    assert round(float(debit_2040), 2) == expected_residual
    assert round(float(credit_expense), 2) == expected_residual


def test_invoice_linked_equal_amount_creates_no_adjustment(phase5_context) -> None:
    context = phase5_context
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    accrual, _ = _find_linked_accrual(context, comparison="under")
    _sync_linked_invoice_amount(context, str(accrual["EntryNumber"]), round(float(accrual["TotalAmount"]), 2))
    generate_accrual_adjustment_journals(context)

    adjustments = context.tables["JournalEntry"].loc[
        context.tables["JournalEntry"]["EntryType"].eq("Accrual Adjustment")
        & context.tables["JournalEntry"]["ReversesJournalEntryID"].notna()
    ]
    adjustments = adjustments.loc[adjustments["ReversesJournalEntryID"].astype(int).eq(int(accrual["JournalEntryID"]))]
    assert adjustments.empty


def test_invoice_linked_over_accrual_expenses_only_the_excess(phase5_context) -> None:
    context = phase5_context
    context.settings = replace(context.settings, anomaly_mode="none")

    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)

    accrual, invoice_line = _find_linked_accrual(context, comparison="over")
    expense_account_number = _accrual_expense_account_number(context, int(accrual["JournalEntryID"]))
    invoice_gl = context.tables["GLEntry"].loc[
        context.tables["GLEntry"]["SourceDocumentType"].eq("PurchaseInvoice")
        & context.tables["GLEntry"]["SourceDocumentID"].astype(int).eq(int(invoice_line["PurchaseInvoiceID"]))
    ]
    line_gl = invoice_gl.loc[invoice_gl["SourceLineID"].notna()].copy()
    line_gl = line_gl.loc[line_gl["SourceLineID"].astype(int).eq(int(invoice_line["PILineID"]))]
    header_gl = invoice_gl.loc[invoice_gl["SourceLineID"].isna()]

    debit_2040 = line_gl.loc[line_gl["AccountID"].astype(int).eq(_account_id_by_number(context, "2040")), "Debit"].sum()
    debit_expense = line_gl.loc[
        line_gl["AccountID"].astype(int).eq(_account_id_by_number(context, expense_account_number)),
        "Debit",
    ].sum()
    credit_2010 = header_gl.loc[header_gl["AccountID"].astype(int).eq(_account_id_by_number(context, "2010")), "Credit"].sum()

    expected_accrual = round(float(accrual["TotalAmount"]), 2)
    expected_excess = round(float(invoice_line["LineTotal"]) - float(accrual["TotalAmount"]), 2)
    expected_invoice_total = round(float(invoice_line["LineTotal"]), 2)
    assert round(float(debit_2040), 2) == expected_accrual
    assert round(float(debit_expense), 2) == expected_excess
    assert round(float(credit_2010), 2) == expected_invoice_total

    adjustments = context.tables["JournalEntry"].loc[
        context.tables["JournalEntry"]["EntryType"].eq("Accrual Adjustment")
        & context.tables["JournalEntry"]["ReversesJournalEntryID"].notna()
    ]
    adjustments = adjustments.loc[adjustments["ReversesJournalEntryID"].astype(int).eq(int(accrual["JournalEntryID"]))]
    assert adjustments.empty


def test_phase8_journal_anomalies_preserve_gl_balance(phase5_context) -> None:
    context = phase5_context

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
    assert results["journal_controls"]["exception_count"] >= 0
    assert len(weekend_years) > 1
    assert "same_creator_approver_journal" in anomaly_types
    assert "missing_reversal_link" not in anomaly_types
    assert "late_reversal" not in anomaly_types
    assert "round_dollar_manual_journal" not in anomaly_types
