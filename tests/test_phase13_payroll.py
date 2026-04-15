from __future__ import annotations

import pandas as pd

from generator_dataset.main import build_phase13
from generator_dataset.schema import TABLE_COLUMNS


def test_phase13_schema_extensions_exist() -> None:
    for table_name in [
        "PayrollPeriod",
        "LaborTimeEntry",
        "PayrollRegister",
        "PayrollRegisterLine",
        "PayrollPayment",
        "PayrollLiabilityRemittance",
    ]:
        assert table_name in TABLE_COLUMNS

    for column_name in [
        "PayClass",
        "BaseHourlyRate",
        "BaseAnnualSalary",
        "StandardHoursPerWeek",
        "OvertimeEligible",
    ]:
        assert column_name in TABLE_COLUMNS["Employee"]

    for column_name in [
        "StandardLaborHoursPerUnit",
        "StandardDirectLaborCost",
        "StandardVariableOverheadCost",
        "StandardFixedOverheadCost",
    ]:
        assert column_name in TABLE_COLUMNS["Item"]


def test_phase13_helper_generates_clean_payroll_and_costing_dataset() -> None:
    context = build_phase13()
    phase13 = context.validation_results["phase13"]

    assert phase13["exceptions"] == []
    assert phase13["payroll_controls"]["exception_count"] == 0
    assert len(context.tables["PayrollPeriod"]) > 0
    assert len(context.tables["LaborTimeEntry"]) > 0
    assert len(context.tables["PayrollRegister"]) > 0
    assert len(context.tables["PayrollRegisterLine"]) > 0
    assert len(context.tables["PayrollPayment"]) > 0
    assert len(context.tables["PayrollLiabilityRemittance"]) > 0

    processed_periods = context.tables["PayrollPeriod"][context.tables["PayrollPeriod"]["Status"].eq("Processed")]
    assert len(processed_periods) > 0
    assert pd.to_datetime(processed_periods["PeriodStartDate"]).sort_values().is_monotonic_increasing

    labor_entries = context.tables["LaborTimeEntry"]
    direct_entries = labor_entries[labor_entries["LaborType"].eq("Direct Manufacturing")].copy()
    assert len(direct_entries) > 0
    assert direct_entries["WorkOrderID"].notna().all()

    work_orders = context.tables["WorkOrder"].set_index("WorkOrderID")
    items = context.tables["Item"].set_index("ItemID")
    assert direct_entries["WorkOrderID"].astype(int).map(work_orders["ItemID"]).map(items["SupplyMode"]).eq("Manufactured").all()


def test_phase13_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase13 = context.validation_results["phase13"]
    row_counts = phase13["row_counts"]

    assert phase13["exceptions"] == []
    assert phase13["gl_balance"]["exception_count"] == 0
    assert phase13["trial_balance_difference"] == 0
    assert phase13["account_rollforward"]["exception_count"] == 0
    assert phase13["o2c_controls"]["exception_count"] == 0
    assert phase13["p2p_controls"]["exception_count"] == 0
    assert phase13["journal_controls"]["exception_count"] == 0
    assert phase13["manufacturing_controls"]["exception_count"] == 0
    assert phase13["payroll_controls"]["exception_count"] == 0

    assert row_counts["PayrollPeriod"] > 100
    assert row_counts["LaborTimeEntry"] > 0
    assert row_counts["PayrollRegister"] > 0
    assert row_counts["PayrollRegisterLine"] > row_counts["PayrollRegister"]
    assert row_counts["PayrollPayment"] == row_counts["PayrollRegister"]
    assert row_counts["PayrollLiabilityRemittance"] > 0
