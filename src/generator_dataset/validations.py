from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from generator_dataset.journals import ACCRUAL_ACCOUNT_METADATA, accrual_journal_details
from generator_dataset.master_data import ACCRUAL_SERVICE_ITEMS
from generator_dataset.manufacturing import (
    CAPACITY_EXCEPTION_REASONS,
    active_routing_by_item,
    manufacturing_capacity_state,
    manufacturing_open_state,
    open_work_order_remaining_quantity_map,
    routing_operations_by_routing,
    scheduled_work_order_ids,
    work_order_operation_schedule_by_operation,
    work_order_operations_by_work_order,
    work_order_actual_conversion_cost_map,
    work_order_completed_quantity_map,
    work_order_material_issue_cost_map,
    work_order_schedule_bounds,
    work_order_standard_direct_labor_cost_map,
    work_order_standard_overhead_cost_map,
    work_order_standard_conversion_cost_map,
    work_order_standard_material_cost_map,
)
from generator_dataset.o2c import (
    credit_memo_allocation_map,
    credit_memo_refunded_amounts,
    invoice_cash_application_amounts,
    invoice_credit_memo_amounts,
    invoice_settled_amounts,
    o2c_receivables_metrics,
    opening_inventory_map,
    o2c_open_state,
    receipt_applied_amounts,
    sales_order_line_shipped_quantities,
    shipment_line_billed_quantities,
    shipment_line_returned_quantities,
)
from generator_dataset.p2p import (
    goods_receipt_line_invoiced_quantities,
    invoice_paid_amounts,
    po_line_received_quantities,
    purchase_invoice_line_matched_basis_map,
)
from generator_dataset.payroll import (
    approved_time_clock_hours_by_employee_period,
    employee_shift_roster_lookup,
    overtime_approval_lookup,
    monthly_direct_labor_reclass_amount,
    monthly_factory_overhead_amount,
    monthly_manufacturing_overhead_pool_amount,
    payroll_liability_recorded_amounts,
    payroll_liability_remitted_amounts,
    time_clock_entry_lookup,
    time_clock_punches_by_entry,
)
from generator_dataset.planning import first_forecast_week_start
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, qty


def planning_week_start(value: pd.Timestamp | str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value).normalize()
    return timestamp - pd.Timedelta(days=int(timestamp.weekday()))


def account_id_by_number(context: GenerationContext, account_number: str) -> int:
    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str).eq(account_number), "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def validate_phase1(context: GenerationContext) -> dict[str, Any]:
    results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": [],
    }

    for table_name, expected_columns in TABLE_COLUMNS.items():
        actual_columns = context.tables[table_name].columns.tolist()
        if actual_columns != expected_columns:
            results["exceptions"].append(f"{table_name} columns do not match schema.")

    if context.tables["Account"]["AccountNumber"].duplicated().any():
        results["exceptions"].append("Duplicate account numbers found.")

    if context.tables["CostCenter"]["ManagerID"].isna().any():
        results["exceptions"].append("One or more cost centers are missing managers.")

    context.validation_results["phase1"] = results
    return results


def validate_phase2(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase1(context)
    exceptions = list(results["exceptions"])

    expected_counts = {
        "Item": context.settings.item_count + len(ACCRUAL_SERVICE_ITEMS),
        "Customer": context.settings.customer_count,
        "Supplier": context.settings.supplier_count,
    }
    for table_name, expected_count in expected_counts.items():
        actual_count = len(context.tables[table_name])
        if actual_count != expected_count:
            exceptions.append(f"{table_name} row count {actual_count} does not match expected {expected_count}.")

    if context.tables["Item"]["ItemCode"].duplicated().any():
        exceptions.append("Duplicate item codes found.")
    if context.tables["Customer"]["CustomerID"].duplicated().any():
        exceptions.append("Duplicate customer IDs found.")
    if context.tables["Supplier"]["SupplierID"].duplicated().any():
        exceptions.append("Duplicate supplier IDs found.")

    gl = context.tables["GLEntry"]
    if gl.empty:
        exceptions.append("Opening balance GL entries were not generated.")
    else:
        difference = round(float(gl["Debit"].sum()) - float(gl["Credit"].sum()), 2)
        if difference != 0:
            exceptions.append(f"Opening balance GL is not balanced: {difference}.")

    budget_count = len(context.tables["Budget"])
    if not 2000 <= budget_count <= 4500:
        exceptions.append(f"Budget row count {budget_count} is outside the 2,000 to 4,500 target.")

    phase2_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
    }
    context.validation_results["phase2"] = phase2_results
    return phase2_results


def validate_phase3(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase2(context)
    exceptions = list(results["exceptions"])

    required_non_empty = [
        "SalesOrder",
        "SalesOrderLine",
        "PurchaseRequisition",
        "PurchaseOrder",
        "PurchaseOrderLine",
    ]
    for table_name in required_non_empty:
        if context.tables[table_name].empty:
            exceptions.append(f"{table_name} was not generated.")

    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    if not sales_orders.empty and not sales_order_lines.empty:
        line_totals = sales_order_lines.groupby("SalesOrderID")["LineTotal"].sum().round(2)
        header_totals = sales_orders.set_index("SalesOrderID")["OrderTotal"].astype(float).round(2)
        mismatched_ids = [
            int(order_id)
            for order_id, total in header_totals.items()
            if round(float(line_totals.get(order_id, -1)), 2) != round(float(total), 2)
        ]
        if mismatched_ids:
            exceptions.append(f"Sales order header totals do not match lines: {mismatched_ids[:5]}.")

    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    if not purchase_orders.empty and not purchase_order_lines.empty:
        line_totals = purchase_order_lines.groupby("PurchaseOrderID")["LineTotal"].sum().round(2)
        header_totals = purchase_orders.set_index("PurchaseOrderID")["OrderTotal"].astype(float).round(2)
        mismatched_ids = [
            int(order_id)
            for order_id, total in header_totals.items()
            if round(float(line_totals.get(order_id, -1)), 2) != round(float(total), 2)
        ]
        if mismatched_ids:
            exceptions.append(f"Purchase order header totals do not match lines: {mismatched_ids[:5]}.")

    if not sales_order_lines.empty:
        valid_order_ids = set(sales_orders["SalesOrderID"].astype(int))
        line_order_ids = set(sales_order_lines["SalesOrderID"].astype(int))
        orphan_ids = sorted(line_order_ids - valid_order_ids)
        if orphan_ids:
            exceptions.append(f"Sales order lines reference missing orders: {orphan_ids[:5]}.")

    if not purchase_order_lines.empty:
        valid_po_ids = set(purchase_orders["PurchaseOrderID"].astype(int))
        line_po_ids = set(purchase_order_lines["PurchaseOrderID"].astype(int))
        orphan_ids = sorted(line_po_ids - valid_po_ids)
        if orphan_ids:
            exceptions.append(f"Purchase order lines reference missing POs: {orphan_ids[:5]}.")

    phase3_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
    }
    context.validation_results["phase3"] = phase3_results
    return phase3_results


def validate_phase4(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase3(context)
    exceptions = list(results["exceptions"])

    required_non_empty = [
        "Shipment",
        "ShipmentLine",
        "GoodsReceipt",
        "GoodsReceiptLine",
    ]
    for table_name in required_non_empty:
        if context.tables[table_name].empty:
            exceptions.append(f"{table_name} was not generated.")

    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    sales_order_lines = context.tables["SalesOrderLine"]
    if not shipment_lines.empty:
        valid_shipment_ids = set(shipments["ShipmentID"].astype(int))
        line_shipment_ids = set(shipment_lines["ShipmentID"].astype(int))
        orphan_ids = sorted(line_shipment_ids - valid_shipment_ids)
        if orphan_ids:
            exceptions.append(f"Shipment lines reference missing shipments: {orphan_ids[:5]}.")

        valid_sales_line_ids = set(sales_order_lines["SalesOrderLineID"].astype(int))
        shipped_sales_line_ids = set(shipment_lines["SalesOrderLineID"].astype(int))
        orphan_sales_line_ids = sorted(shipped_sales_line_ids - valid_sales_line_ids)
        if orphan_sales_line_ids:
            exceptions.append(f"Shipment lines reference missing sales order lines: {orphan_sales_line_ids[:5]}.")

        shipped_quantity = shipment_lines.groupby("SalesOrderLineID")["QuantityShipped"].sum()
        ordered_quantity = sales_order_lines.set_index("SalesOrderLineID")["Quantity"].astype(float)
        over_shipped = [
            int(line_id)
            for line_id, shipped in shipped_quantity.items()
            if round(float(shipped), 2) > round(float(ordered_quantity.get(line_id, 0.0)), 2)
        ]
        if over_shipped:
            exceptions.append(f"Shipment lines exceed ordered quantity: {over_shipped[:5]}.")

    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    if not goods_receipt_lines.empty:
        valid_receipt_ids = set(goods_receipts["GoodsReceiptID"].astype(int))
        line_receipt_ids = set(goods_receipt_lines["GoodsReceiptID"].astype(int))
        orphan_ids = sorted(line_receipt_ids - valid_receipt_ids)
        if orphan_ids:
            exceptions.append(f"Goods receipt lines reference missing goods receipts: {orphan_ids[:5]}.")

        valid_po_line_ids = set(purchase_order_lines["POLineID"].astype(int))
        received_po_line_ids = set(goods_receipt_lines["POLineID"].astype(int))
        orphan_po_line_ids = sorted(received_po_line_ids - valid_po_line_ids)
        if orphan_po_line_ids:
            exceptions.append(f"Goods receipt lines reference missing PO lines: {orphan_po_line_ids[:5]}.")

        received_quantity = goods_receipt_lines.groupby("POLineID")["QuantityReceived"].sum()
        ordered_quantity = purchase_order_lines.set_index("POLineID")["Quantity"].astype(float)
        over_received = [
            int(line_id)
            for line_id, received in received_quantity.items()
            if round(float(received), 2) > round(float(ordered_quantity.get(line_id, 0.0)), 2)
        ]
        if over_received:
            exceptions.append(f"Goods receipt lines exceed PO quantity: {over_received[:5]}.")

    phase4_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
    }
    context.validation_results["phase4"] = phase4_results
    return phase4_results


def validate_phase5(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase4(context)
    exceptions = list(results["exceptions"])

    required_non_empty = [
        "SalesInvoice",
        "SalesInvoiceLine",
        "CashReceipt",
        "CashReceiptApplication",
        "PurchaseInvoice",
        "PurchaseInvoiceLine",
        "DisbursementPayment",
    ]
    for table_name in required_non_empty:
        if context.tables[table_name].empty:
            exceptions.append(f"{table_name} was not generated.")

    sales_invoices = context.tables["SalesInvoice"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    if not sales_invoice_lines.empty:
        valid_invoice_ids = set(sales_invoices["SalesInvoiceID"].astype(int))
        line_invoice_ids = set(sales_invoice_lines["SalesInvoiceID"].astype(int))
        orphan_ids = sorted(line_invoice_ids - valid_invoice_ids)
        if orphan_ids:
            exceptions.append(f"Sales invoice lines reference missing invoices: {orphan_ids[:5]}.")

        line_totals = sales_invoice_lines.groupby("SalesInvoiceID")["LineTotal"].sum().round(2)
        header_totals = sales_invoices.set_index("SalesInvoiceID")["SubTotal"].astype(float).round(2)
        mismatched_ids = [
            int(invoice_id)
            for invoice_id, total in header_totals.items()
            if round(float(line_totals.get(invoice_id, -1)), 2) != round(float(total), 2)
        ]
        if mismatched_ids:
            exceptions.append(f"Sales invoice subtotals do not match lines: {mismatched_ids[:5]}.")

    cash_receipts = context.tables["CashReceipt"]
    cash_receipt_applications = context.tables["CashReceiptApplication"]
    if not cash_receipts.empty:
        valid_invoice_ids = set(sales_invoices["SalesInvoiceID"].astype(int))
        receipt_invoice_ids = set(cash_receipts["SalesInvoiceID"].dropna().astype(int))
        orphan_ids = sorted(receipt_invoice_ids - valid_invoice_ids)
        if orphan_ids:
            exceptions.append(f"Cash receipts reference missing sales invoices: {orphan_ids[:5]}.")

    if not cash_receipt_applications.empty:
        valid_receipt_ids = set(cash_receipts["CashReceiptID"].astype(int))
        application_receipt_ids = set(cash_receipt_applications["CashReceiptID"].astype(int))
        orphan_receipts = sorted(application_receipt_ids - valid_receipt_ids)
        if orphan_receipts:
            exceptions.append(f"Cash receipt applications reference missing receipts: {orphan_receipts[:5]}.")

        valid_invoice_ids = set(sales_invoices["SalesInvoiceID"].astype(int))
        application_invoice_ids = set(cash_receipt_applications["SalesInvoiceID"].astype(int))
        orphan_invoices = sorted(application_invoice_ids - valid_invoice_ids)
        if orphan_invoices:
            exceptions.append(f"Cash receipt applications reference missing sales invoices: {orphan_invoices[:5]}.")

        applied_by_receipt = receipt_applied_amounts(context)
        for receipt in cash_receipts.itertuples(index=False):
            if round(float(applied_by_receipt.get(int(receipt.CashReceiptID), 0.0)), 2) > round(float(receipt.Amount), 2):
                exceptions.append(f"Cash receipt applications exceed receipt amount: {int(receipt.CashReceiptID)}.")

        settled_by_invoice = invoice_settled_amounts(context)
        for invoice in sales_invoices.itertuples(index=False):
            if round(float(settled_by_invoice.get(int(invoice.SalesInvoiceID), 0.0)), 2) > round(float(invoice.GrandTotal), 2):
                exceptions.append(f"Sales invoice settlements exceed invoice total: {int(invoice.SalesInvoiceID)}.")

    purchase_invoices = context.tables["PurchaseInvoice"]
    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    if not purchase_invoice_lines.empty:
        valid_invoice_ids = set(purchase_invoices["PurchaseInvoiceID"].astype(int))
        line_invoice_ids = set(purchase_invoice_lines["PurchaseInvoiceID"].astype(int))
        orphan_ids = sorted(line_invoice_ids - valid_invoice_ids)
        if orphan_ids:
            exceptions.append(f"Purchase invoice lines reference missing invoices: {orphan_ids[:5]}.")

        line_totals = purchase_invoice_lines.groupby("PurchaseInvoiceID")["LineTotal"].sum().round(2)
        header_totals = purchase_invoices.set_index("PurchaseInvoiceID")["SubTotal"].astype(float).round(2)
        mismatched_ids = [
            int(invoice_id)
            for invoice_id, total in header_totals.items()
            if round(float(line_totals.get(invoice_id, -1)), 2) != round(float(total), 2)
        ]
        if mismatched_ids:
            exceptions.append(f"Purchase invoice subtotals do not match lines: {mismatched_ids[:5]}.")

    disbursements = context.tables["DisbursementPayment"]
    if not disbursements.empty:
        valid_invoice_ids = set(purchase_invoices["PurchaseInvoiceID"].astype(int))
        payment_invoice_ids = set(disbursements["PurchaseInvoiceID"].dropna().astype(int))
        orphan_ids = sorted(payment_invoice_ids - valid_invoice_ids)
        if orphan_ids:
            exceptions.append(f"Disbursements reference missing purchase invoices: {orphan_ids[:5]}.")

        payment_totals = disbursements.groupby("PurchaseInvoiceID")["Amount"].sum().round(2)
        invoice_totals = purchase_invoices.set_index("PurchaseInvoiceID")["GrandTotal"].astype(float).round(2)
        overpaid = [
            int(invoice_id)
            for invoice_id, amount in payment_totals.items()
            if round(float(amount), 2) > round(float(invoice_totals.get(invoice_id, 0.0)), 2)
        ]
        if overpaid:
            exceptions.append(f"Disbursements exceed purchase invoice totals: {overpaid[:5]}.")

    phase5_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
    }
    context.validation_results["phase5"] = phase5_results
    return phase5_results


def validate_gl_balance(context: GenerationContext) -> dict[str, Any]:
    gl = context.tables["GLEntry"]
    if gl.empty:
        return {"exception_count": 1, "exceptions": [{"message": "GLEntry is empty."}]}

    grouped = gl.groupby(["VoucherType", "VoucherNumber"], dropna=False)[["Debit", "Credit"]].sum()
    grouped["Difference"] = (grouped["Debit"].astype(float) - grouped["Credit"].astype(float)).round(2)
    exceptions = grouped[grouped["Difference"].ne(0)].reset_index()
    return {
        "exception_count": int(len(exceptions)),
        "exceptions": exceptions.to_dict(orient="records"),
    }


def validate_account_rollforward(context: GenerationContext) -> dict[str, Any]:
    gl = context.tables["GLEntry"]
    operational_gl = gl[~gl["SourceDocumentType"].eq("JournalEntry")].copy()
    exceptions: list[dict[str, Any]] = []

    def gl_debit_net(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = operational_gl[operational_gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Debit"].sum()) - float(account_rows["Credit"].sum()), 2)

    def gl_debit_net_all(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = gl[gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Debit"].sum()) - float(account_rows["Credit"].sum()), 2)

    def gl_credit_net(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = operational_gl[operational_gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Credit"].sum()) - float(account_rows["Debit"].sum()), 2)

    def gl_credit_net_all(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = gl[gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Credit"].sum()) - float(account_rows["Debit"].sum()), 2)

    matched_basis_map = purchase_invoice_line_matched_basis_map(context)
    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    inventory_invoice_line_ids = set(
        purchase_invoice_lines.loc[purchase_invoice_lines["GoodsReceiptLineID"].notna(), "PILineID"].astype(int).tolist()
    ) if not purchase_invoice_lines.empty else set()
    cleared_grni = round(
        sum(
            float(amount)
            for piline_id, amount in matched_basis_map.items()
            if int(piline_id) in inventory_invoice_line_ids
        ),
        2,
    )
    accrued_expense_opening_balance = journal_entry_type_amount_by_account(context, "Opening", "2040")
    accrued_expense_accrual_total = round(
        sum(float(entry["Amount"]) for entry in accrual_journal_details(context)),
        2,
    )
    accrued_expense_clear_total = round(
        sum(float(value) for value in accrued_service_clear_amounts_by_journal(context).values()),
        2,
    )
    accrued_expense_adjustment_total = round(
        sum(float(value) for value in accrued_adjustment_amounts_by_journal(context).values()),
        2,
    )
    credit_memo_allocations = credit_memo_allocation_map(context)
    customer_credit_total = round(
        sum(float(allocation["customer_credit_amount"]) for allocation in credit_memo_allocations.values()),
        2,
    )
    cash_applications_total = round(float(context.tables["CashReceiptApplication"]["AppliedAmount"].sum()), 2)
    ar_credit_memo_total = round(
        sum(float(allocation["ar_amount"]) for allocation in credit_memo_allocations.values()),
        2,
    )
    payroll_recorded = payroll_liability_recorded_amounts(context)
    payroll_remitted = payroll_liability_remitted_amounts(context)
    payroll_register_lookup = (
        context.tables["PayrollRegister"].set_index("PayrollRegisterID")["NetPay"].astype(float).to_dict()
        if not context.tables["PayrollRegister"].empty
        else {}
    )
    payroll_paid_total = round(
        sum(
            float(payroll_register_lookup.get(int(payment.PayrollRegisterID), 0.0))
            for payment in context.tables["PayrollPayment"].itertuples(index=False)
        ),
        2,
    )
    checks = [
        {
            "name": "AR",
            "expected": round(
                float(context.tables["SalesInvoice"]["GrandTotal"].sum())
                - cash_applications_total
                - ar_credit_memo_total,
                2,
            ),
            "actual": gl_debit_net("1020"),
        },
        {
            "name": "Customer Deposits and Unapplied Cash",
            "expected": round(
                float(context.tables["CashReceipt"]["Amount"].sum())
                + customer_credit_total
                - cash_applications_total
                - float(context.tables["CustomerRefund"]["Amount"].sum()),
                2,
            ),
            "actual": gl_credit_net("2060"),
        },
        {
            "name": "AP",
            "expected": round(
                float(context.tables["PurchaseInvoice"]["GrandTotal"].sum())
                - float(context.tables["DisbursementPayment"]["Amount"].sum()),
                2,
            ),
            "actual": gl_credit_net("2010"),
        },
        {
            "name": "Inventory",
            "expected": round(
                float(context.tables["GoodsReceiptLine"]["ExtendedStandardCost"].sum())
                + float(context.tables["ProductionCompletionLine"]["ExtendedStandardTotalCost"].sum())
                + float(context.tables["SalesReturnLine"]["ExtendedStandardCost"].sum())
                - float(context.tables["MaterialIssueLine"]["ExtendedStandardCost"].sum())
                - float(context.tables["ShipmentLine"]["ExtendedStandardCost"].sum()),
                2,
            ),
            "actual": gl_debit_net("1040") + gl_debit_net("1045"),
        },
        {
            "name": "COGS",
            "expected": round(
                float(context.tables["ShipmentLine"]["ExtendedStandardCost"].sum())
                - float(context.tables["SalesReturnLine"]["ExtendedStandardCost"].sum()),
                2,
            ),
            "actual": round(
                gl_debit_net("5010") + gl_debit_net("5020") + gl_debit_net("5030") + gl_debit_net("5040"),
                2,
            ),
        },
        {
            "name": "Sales Tax Payable",
            "expected": round(
                float(context.tables["SalesInvoice"]["TaxAmount"].sum())
                - float(context.tables["CreditMemo"]["TaxAmount"].sum()),
                2,
            ),
            "actual": gl_credit_net("2050"),
        },
        {
            "name": "Sales Returns and Allowances",
            "expected": round(float(context.tables["CreditMemo"]["SubTotal"].sum()), 2),
            "actual": gl_debit_net("4060"),
        },
        {
            "name": "GRNI",
            "expected": round(
                float(context.tables["GoodsReceiptLine"]["ExtendedStandardCost"].sum()) - cleared_grni,
                2,
            ),
            "actual": gl_credit_net("2020"),
        },
        {
            "name": "Accrued Expenses",
            "expected": round(
                accrued_expense_opening_balance
                + accrued_expense_accrual_total
                - accrued_expense_clear_total
                - accrued_expense_adjustment_total,
                2,
            ),
            "actual": gl_credit_net_all("2040"),
        },
        {
            "name": "WIP",
            "expected": round(
                float(context.tables["MaterialIssueLine"]["ExtendedStandardCost"].sum())
                - float(context.tables["ProductionCompletionLine"]["ExtendedStandardMaterialCost"].sum())
                - float(context.tables["WorkOrderClose"]["MaterialVarianceAmount"].sum()),
                2,
            ),
            "actual": gl_debit_net("1046"),
        },
        {
            "name": "Manufacturing Cost Clearing",
            "expected": round(
                float(sum(work_order_actual_conversion_cost_map(context).values()))
                - float(context.tables["ProductionCompletionLine"]["ExtendedStandardConversionCost"].sum())
                - float(context.tables["WorkOrderClose"]["ConversionVarianceAmount"].sum()),
                2,
            ),
            "actual": gl_debit_net_all("1090"),
        },
        {
            "name": "Manufacturing Variance",
            "expected": round(float(context.tables["WorkOrderClose"]["TotalVarianceAmount"].sum()), 2),
            "actual": gl_debit_net("5080"),
        },
        {
            "name": "Accrued Payroll",
            "expected": round(
                float(payroll_recorded.get("2030", 0.0))
                - payroll_paid_total,
                2,
            ),
            "actual": gl_credit_net("2030"),
        },
        {
            "name": "Payroll Tax Withholdings Payable",
            "expected": round(float(payroll_recorded.get("2031", 0.0)) - float(payroll_remitted.get("2031", 0.0)), 2),
            "actual": gl_credit_net("2031"),
        },
        {
            "name": "Employer Payroll Taxes Payable",
            "expected": round(float(payroll_recorded.get("2032", 0.0)) - float(payroll_remitted.get("2032", 0.0)), 2),
            "actual": gl_credit_net("2032"),
        },
        {
            "name": "Benefits and Other Deductions Payable",
            "expected": round(float(payroll_recorded.get("2033", 0.0)) - float(payroll_remitted.get("2033", 0.0)), 2),
            "actual": gl_credit_net("2033"),
        },
    ]

    for check in checks:
        if abs(round(float(check["expected"]) - float(check["actual"]), 2)) > 0.01:
            exceptions.append(check)

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_p2p_phase9_controls(context: GenerationContext) -> dict[str, Any]:
    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    requisitions = context.tables["PurchaseRequisition"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    journal_entries = context.tables["JournalEntry"]
    items = context.tables["Item"]
    purchase_invoices = context.tables["PurchaseInvoice"]
    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    exceptions: list[dict[str, Any]] = []

    requisition_item_ids = requisitions.set_index("RequisitionID")["ItemID"].to_dict() if not requisitions.empty else {}
    valid_requisition_ids = set(requisitions["RequisitionID"].astype(int)) if not requisitions.empty else set()
    valid_accrual_journal_ids = set(
        journal_entries.loc[journal_entries["EntryType"].eq("Accrual"), "JournalEntryID"].astype(int).tolist()
    ) if not journal_entries.empty else set()
    item_group_lookup = items.set_index("ItemID")["ItemGroup"].to_dict() if not items.empty else {}
    valid_goods_receipt_line_ids = (
        set(goods_receipt_lines["GoodsReceiptLineID"].astype(int)) if not goods_receipt_lines.empty else set()
    )
    goods_receipt_lookup = (
        goods_receipt_lines.set_index("GoodsReceiptLineID")[["POLineID", "ItemID", "QuantityReceived"]].to_dict("index")
        if not goods_receipt_lines.empty
        else {}
    )

    if not purchase_order_lines.empty:
        linked_po_lines = purchase_order_lines[purchase_order_lines["RequisitionID"].notna()]
        orphan_requisition_ids = sorted(
            set(linked_po_lines["RequisitionID"].astype(int)) - valid_requisition_ids
        )
        if orphan_requisition_ids:
            exceptions.append({
                "type": "po_line_missing_requisition",
                "message": f"Purchase order lines reference missing requisitions: {orphan_requisition_ids[:5]}.",
            })

        mismatched_line_items = [
            int(line.POLineID)
            for line in linked_po_lines.itertuples(index=False)
            if int(requisition_item_ids.get(int(line.RequisitionID), line.ItemID)) != int(line.ItemID)
        ]
        if mismatched_line_items:
            exceptions.append({
                "type": "po_line_item_mismatch",
                "message": f"Purchase order lines do not match requisition items: {mismatched_line_items[:5]}.",
            })

        for purchase_order in purchase_orders.itertuples(index=False):
            related_lines = purchase_order_lines[
                purchase_order_lines["PurchaseOrderID"].astype(int).eq(int(purchase_order.PurchaseOrderID))
            ]
            if related_lines.empty:
                continue

            line_requisition_ids = set(related_lines["RequisitionID"].dropna().astype(int).tolist())
            if pd.notna(purchase_order.RequisitionID):
                if len(line_requisition_ids) != 1 or int(purchase_order.RequisitionID) not in line_requisition_ids:
                    exceptions.append({
                        "type": "po_header_requisition_mismatch",
                        "purchase_order_id": int(purchase_order.PurchaseOrderID),
                        "message": "Purchase order header RequisitionID does not match its line-level requisition links.",
                    })
            elif len(line_requisition_ids) == 1:
                exceptions.append({
                    "type": "po_header_missing_requisition",
                    "purchase_order_id": int(purchase_order.PurchaseOrderID),
                    "message": "Purchase order header RequisitionID should be populated when all PO lines share one requisition.",
                })

        received_quantities = po_line_received_quantities(context)
        for purchase_order in purchase_orders.itertuples(index=False):
            related_lines = purchase_order_lines[
                purchase_order_lines["PurchaseOrderID"].astype(int).eq(int(purchase_order.PurchaseOrderID))
            ]
            if related_lines.empty:
                continue

            received_total = 0.0
            all_fully_received = True
            for line in related_lines.itertuples(index=False):
                received_quantity = float(received_quantities.get(int(line.POLineID), 0.0))
                received_total += received_quantity
                if round(received_quantity, 2) < round(float(line.Quantity), 2):
                    all_fully_received = False

            expected_status = "Open" if round(received_total, 2) <= 0 else "Received" if all_fully_received else "Partially Received"
            if str(purchase_order.Status) != expected_status:
                exceptions.append({
                    "type": "po_status_mismatch",
                    "purchase_order_id": int(purchase_order.PurchaseOrderID),
                    "message": f"Purchase order status {purchase_order.Status} does not match expected {expected_status}.",
                })

    if not purchase_invoice_lines.empty:
        service_invoice_lines = purchase_invoice_lines[purchase_invoice_lines["AccrualJournalEntryID"].notna()]
        if not service_invoice_lines.empty:
            invalid_accrual_ids = sorted(
                set(service_invoice_lines["AccrualJournalEntryID"].astype(int)) - valid_accrual_journal_ids
            )
            if invalid_accrual_ids:
                exceptions.append({
                    "type": "invoice_line_missing_accrual_journal",
                    "message": f"Accrued service invoice lines reference missing accrual journals: {invalid_accrual_ids[:5]}.",
                })

            service_lines_with_receipts = service_invoice_lines[service_invoice_lines["GoodsReceiptLineID"].notna()]
            if not service_lines_with_receipts.empty:
                exceptions.append({
                    "type": "service_invoice_line_has_receipt",
                    "message": "Accrued service invoice lines should not reference goods receipt lines.",
                })

            service_lines_with_po = service_invoice_lines[service_invoice_lines["POLineID"].notna()]
            if not service_lines_with_po.empty:
                exceptions.append({
                    "type": "service_invoice_line_has_po_line",
                    "message": "Accrued service invoice lines should not reference PO lines.",
                })

            non_service_items = [
                int(line.PILineID)
                for line in service_invoice_lines.itertuples(index=False)
                if str(item_group_lookup.get(int(line.ItemID), "")) != "Services"
            ]
            if non_service_items:
                exceptions.append({
                    "type": "service_invoice_item_mismatch",
                    "message": f"Accrued service invoice lines do not use service items: {non_service_items[:5]}.",
                })

        linked_invoice_lines = purchase_invoice_lines[purchase_invoice_lines["GoodsReceiptLineID"].notna()]
        orphan_receipt_line_ids = sorted(
            set(linked_invoice_lines["GoodsReceiptLineID"].astype(int)) - valid_goods_receipt_line_ids
        )
        if orphan_receipt_line_ids:
            exceptions.append({
                "type": "invoice_line_missing_receipt_line",
                "message": f"Purchase invoice lines reference missing goods receipt lines: {orphan_receipt_line_ids[:5]}.",
            })

        po_link_mismatches = []
        item_mismatches = []
        for line in linked_invoice_lines.itertuples(index=False):
            receipt_line = goods_receipt_lookup.get(int(line.GoodsReceiptLineID))
            if receipt_line is None:
                continue
            if int(receipt_line["POLineID"]) != int(line.POLineID):
                po_link_mismatches.append(int(line.PILineID))
            if int(receipt_line["ItemID"]) != int(line.ItemID):
                item_mismatches.append(int(line.PILineID))

        if po_link_mismatches:
            exceptions.append({
                "type": "invoice_line_po_link_mismatch",
                "message": f"Purchase invoice lines do not match their goods receipt line PO links: {po_link_mismatches[:5]}.",
            })
        if item_mismatches:
            exceptions.append({
                "type": "invoice_line_item_mismatch",
                "message": f"Purchase invoice lines do not match their goods receipt line items: {item_mismatches[:5]}.",
            })

        invoiced_quantities = goods_receipt_line_invoiced_quantities(context)
        over_invoiced_receipt_lines = [
            int(goods_receipt_line_id)
            for goods_receipt_line_id, quantity_invoiced in invoiced_quantities.items()
            if round(float(quantity_invoiced), 2)
            > round(float(goods_receipt_lookup.get(int(goods_receipt_line_id), {}).get("QuantityReceived", 0.0)), 2)
        ]
        if over_invoiced_receipt_lines:
            exceptions.append({
                "type": "over_invoiced_receipt_line",
                "message": f"Goods receipt lines are invoiced above received quantity: {over_invoiced_receipt_lines[:5]}.",
            })

        paid_amounts = invoice_paid_amounts(context)
        for invoice in purchase_invoices.itertuples(index=False):
            paid_amount = float(paid_amounts.get(int(invoice.PurchaseInvoiceID), 0.0))
            outstanding_amount = round(float(invoice.GrandTotal) - paid_amount, 2)
            expected_status = "Approved" if paid_amount <= 0 else "Paid" if outstanding_amount <= 0 else "Partially Paid"
            if str(invoice.Status) != expected_status:
                exceptions.append({
                    "type": "purchase_invoice_status_mismatch",
                    "purchase_invoice_id": int(invoice.PurchaseInvoiceID),
                    "message": f"Purchase invoice status {invoice.Status} does not match expected {expected_status}.",
                })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_o2c_phase11_controls(context: GenerationContext) -> dict[str, Any]:
    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    sales_invoices = context.tables["SalesInvoice"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    cash_receipts = context.tables["CashReceipt"]
    cash_receipt_applications = context.tables["CashReceiptApplication"]
    sales_returns = context.tables["SalesReturn"]
    sales_return_lines = context.tables["SalesReturnLine"]
    credit_memos = context.tables["CreditMemo"]
    credit_memo_lines = context.tables["CreditMemoLine"]
    customer_refunds = context.tables["CustomerRefund"]
    exceptions: list[dict[str, Any]] = []

    shipment_lookup = shipment_lines.set_index("ShipmentLineID").to_dict("index") if not shipment_lines.empty else {}
    sales_line_lookup = sales_order_lines.set_index("SalesOrderLineID").to_dict("index") if not sales_order_lines.empty else {}
    invoice_lookup = sales_invoices.set_index("SalesInvoiceID").to_dict("index") if not sales_invoices.empty else {}
    return_line_lookup = sales_return_lines.set_index("SalesReturnLineID").to_dict("index") if not sales_return_lines.empty else {}

    if not sales_invoice_lines.empty:
        linked_invoice_lines = sales_invoice_lines[sales_invoice_lines["ShipmentLineID"].notna()]
        valid_shipment_line_ids = set(shipment_lines["ShipmentLineID"].astype(int)) if not shipment_lines.empty else set()
        orphan_shipment_lines = sorted(set(linked_invoice_lines["ShipmentLineID"].astype(int)) - valid_shipment_line_ids)
        if orphan_shipment_lines:
            exceptions.append({
                "type": "invoice_line_missing_shipment_line",
                "message": f"Sales invoice lines reference missing shipment lines: {orphan_shipment_lines[:5]}.",
            })

        mismatched_invoice_lines = []
        for line in linked_invoice_lines.itertuples(index=False):
            shipment_line = shipment_lookup.get(int(line.ShipmentLineID))
            sales_line = sales_line_lookup.get(int(line.SalesOrderLineID))
            if shipment_line is None or sales_line is None:
                continue
            if int(shipment_line["SalesOrderLineID"]) != int(line.SalesOrderLineID) or int(shipment_line["ItemID"]) != int(line.ItemID) or int(sales_line["ItemID"]) != int(line.ItemID):
                mismatched_invoice_lines.append(int(line.SalesInvoiceLineID))
        if mismatched_invoice_lines:
            exceptions.append({
                "type": "invoice_line_link_mismatch",
                "message": f"Sales invoice lines do not match linked shipment or order lines: {mismatched_invoice_lines[:5]}.",
            })

        invoice_pricing_mismatches = []
        for line in linked_invoice_lines.itertuples(index=False):
            sales_line = sales_line_lookup.get(int(line.SalesOrderLineID))
            if sales_line is None:
                continue
            comparable_fields = ["BaseListPrice", "UnitPrice", "Discount", "PriceListLineID", "PromotionID", "PriceOverrideApprovalID", "PricingMethod"]
            mismatch_found = False
            for field_name in comparable_fields:
                sales_value = sales_line.get(field_name)
                invoice_value = getattr(line, field_name)
                if pd.isna(sales_value) and pd.isna(invoice_value):
                    continue
                if field_name in {"BaseListPrice", "UnitPrice", "Discount"}:
                    if round(float(invoice_value), 4) != round(float(sales_value), 4):
                        mismatch_found = True
                        break
                elif str(invoice_value) != str(sales_value):
                    mismatch_found = True
                    break
            if mismatch_found:
                invoice_pricing_mismatches.append(int(line.SalesInvoiceLineID))
        if invoice_pricing_mismatches:
            exceptions.append({
                "type": "invoice_line_pricing_lineage_mismatch",
                "message": f"Sales invoice lines do not match source order-line pricing lineage: {invoice_pricing_mismatches[:5]}.",
            })

        billed_quantities = shipment_line_billed_quantities(context)
        over_billed_shipment_lines = [
            int(shipment_line_id)
            for shipment_line_id, billed_quantity in billed_quantities.items()
            if round(float(billed_quantity), 2) > round(float(shipment_lookup.get(int(shipment_line_id), {}).get("QuantityShipped", 0.0)), 2)
        ]
        if over_billed_shipment_lines:
            exceptions.append({
                "type": "over_billed_shipment_line",
                "message": f"Shipment lines are billed above shipped quantity: {over_billed_shipment_lines[:5]}.",
            })

    shipped_by_sales_line = sales_order_line_shipped_quantities(context)
    over_shipped_sales_lines = [
        int(line.SalesOrderLineID)
        for line in sales_order_lines.itertuples(index=False)
        if round(float(shipped_by_sales_line.get(int(line.SalesOrderLineID), 0.0)), 2) > round(float(line.Quantity), 2)
    ]
    if over_shipped_sales_lines:
        exceptions.append({
            "type": "over_shipped_sales_line",
            "message": f"Sales order lines are shipped above ordered quantity: {over_shipped_sales_lines[:5]}.",
        })

    if not cash_receipt_applications.empty:
        valid_receipt_ids = set(cash_receipts["CashReceiptID"].astype(int)) if not cash_receipts.empty else set()
        orphan_receipts = sorted(set(cash_receipt_applications["CashReceiptID"].astype(int)) - valid_receipt_ids)
        if orphan_receipts:
            exceptions.append({
                "type": "application_missing_receipt",
                "message": f"Cash receipt applications reference missing receipts: {orphan_receipts[:5]}.",
            })

        valid_invoice_ids = set(sales_invoices["SalesInvoiceID"].astype(int)) if not sales_invoices.empty else set()
        orphan_invoices = sorted(set(cash_receipt_applications["SalesInvoiceID"].astype(int)) - valid_invoice_ids)
        if orphan_invoices:
            exceptions.append({
                "type": "application_missing_invoice",
                "message": f"Cash receipt applications reference missing sales invoices: {orphan_invoices[:5]}.",
            })

        applied_by_receipt = receipt_applied_amounts(context)
        for receipt in cash_receipts.itertuples(index=False):
            if round(float(applied_by_receipt.get(int(receipt.CashReceiptID), 0.0)), 2) > round(float(receipt.Amount), 2):
                exceptions.append({
                    "type": "receipt_overapplied",
                    "cash_receipt_id": int(receipt.CashReceiptID),
                    "message": "Cash receipt applications exceed receipt amount.",
                })

        settled_by_invoice = invoice_settled_amounts(context)
        for invoice in sales_invoices.itertuples(index=False):
            if round(float(settled_by_invoice.get(int(invoice.SalesInvoiceID), 0.0)), 2) > round(float(invoice.GrandTotal), 2):
                exceptions.append({
                    "type": "invoice_oversettled",
                    "sales_invoice_id": int(invoice.SalesInvoiceID),
                    "message": "Invoice settlements exceed invoice total.",
                })

    if not sales_return_lines.empty:
        billed_quantities = shipment_line_billed_quantities(context)
        returned_quantities = shipment_line_returned_quantities(context)
        over_returned_shipment_lines = [
            int(shipment_line_id)
            for shipment_line_id, returned_quantity in returned_quantities.items()
            if round(float(returned_quantity), 2) > round(float(billed_quantities.get(int(shipment_line_id), 0.0)), 2)
        ]
        if over_returned_shipment_lines:
            exceptions.append({
                "type": "over_returned_shipment_line",
                "message": f"Shipment lines are returned above billed quantity: {over_returned_shipment_lines[:5]}.",
            })

    if not credit_memos.empty:
        duplicate_invoice_returns = credit_memos["OriginalSalesInvoiceID"].astype(int).value_counts()
        repeated_return_invoices = sorted(duplicate_invoice_returns[duplicate_invoice_returns.gt(1)].index.astype(int).tolist())
        if repeated_return_invoices:
            exceptions.append({
                "type": "multiple_return_events_per_invoice",
                "message": f"Original sales invoices have more than one return or credit-memo chain: {repeated_return_invoices[:5]}.",
            })

        credit_memo_by_return = credit_memos.set_index("SalesReturnID")["OriginalSalesInvoiceID"].astype(int).to_dict()
        invalid_return_dates = []
        for sales_return in sales_returns.itertuples(index=False):
            original_invoice_id = credit_memo_by_return.get(int(sales_return.SalesReturnID))
            if original_invoice_id is None:
                continue
            original_invoice = invoice_lookup.get(int(original_invoice_id))
            if original_invoice is None:
                continue
            if pd.Timestamp(sales_return.ReturnDate) <= pd.Timestamp(original_invoice["InvoiceDate"]):
                invalid_return_dates.append(int(sales_return.SalesReturnID))
        if invalid_return_dates:
            exceptions.append({
                "type": "return_date_before_or_on_invoice_date",
                "message": f"Sales returns must occur after the original invoice date: {invalid_return_dates[:5]}.",
            })

    if not credit_memo_lines.empty:
        line_mismatches = []
        pricing_mismatches = []
        invoice_lines_by_id = sales_invoice_lines.set_index("SalesInvoiceLineID").to_dict("index") if not sales_invoice_lines.empty else {}
        for credit_memo_line in credit_memo_lines.itertuples(index=False):
            return_line = return_line_lookup.get(int(credit_memo_line.SalesReturnLineID))
            if return_line is None:
                line_mismatches.append(int(credit_memo_line.CreditMemoLineID))
                continue
            memo = credit_memos[credit_memos["CreditMemoID"].astype(int).eq(int(credit_memo_line.CreditMemoID))].iloc[0]
            original_invoice_id = int(memo.OriginalSalesInvoiceID)
            original_invoice_line = sales_invoice_lines[
                sales_invoice_lines["SalesInvoiceID"].astype(int).eq(original_invoice_id)
                & sales_invoice_lines["ShipmentLineID"].astype(int).eq(int(return_line["ShipmentLineID"]))
            ]
            if original_invoice_line.empty:
                line_mismatches.append(int(credit_memo_line.CreditMemoLineID))
                continue
            original_line = original_invoice_line.iloc[0]
            expected_line_total = money(
                float(credit_memo_line.Quantity) * float(original_line["UnitPrice"]) * (1 - float(original_line["Discount"]))
            )
            list_line_mismatch = (
                (pd.notna(credit_memo_line.PriceListLineID) or pd.notna(original_line["PriceListLineID"]))
                and str(credit_memo_line.PriceListLineID) != str(original_line["PriceListLineID"])
            )
            promotion_mismatch = (
                (pd.notna(credit_memo_line.PromotionID) or pd.notna(original_line["PromotionID"]))
                and str(credit_memo_line.PromotionID) != str(original_line["PromotionID"])
            )
            override_mismatch = (
                (pd.notna(credit_memo_line.PriceOverrideApprovalID) or pd.notna(original_line["PriceOverrideApprovalID"]))
                and str(credit_memo_line.PriceOverrideApprovalID) != str(original_line["PriceOverrideApprovalID"])
            )
            if (
                round(float(credit_memo_line.BaseListPrice), 2) != round(float(original_line["BaseListPrice"]), 2)
                or round(float(credit_memo_line.UnitPrice), 2) != round(float(original_line["UnitPrice"]), 2)
                or round(float(credit_memo_line.Discount), 4) != round(float(original_line["Discount"]), 4)
                or money(float(credit_memo_line.LineTotal)) != expected_line_total
                or list_line_mismatch
                or promotion_mismatch
                or override_mismatch
                or str(credit_memo_line.PricingMethod) != str(original_line["PricingMethod"])
            ):
                pricing_mismatches.append(int(credit_memo_line.CreditMemoLineID))
        if line_mismatches:
            exceptions.append({
                "type": "credit_memo_line_return_mismatch",
                "message": f"Credit memo lines do not match valid return lines and original invoices: {line_mismatches[:5]}.",
            })
        if pricing_mismatches:
            exceptions.append({
                "type": "credit_memo_pricing_mismatch",
                "message": f"Credit memo lines do not match original billed pricing: {pricing_mismatches[:5]}.",
            })

    credit_memo_allocations = credit_memo_allocation_map(context)
    refunded_amounts = credit_memo_refunded_amounts(context)
    over_refunded_credit_memos = [
        int(credit_memo_id)
        for credit_memo_id, refunded_amount in refunded_amounts.items()
        if round(float(refunded_amount), 2) > round(float(credit_memo_allocations.get(int(credit_memo_id), {}).get("customer_credit_amount", 0.0)), 2)
    ]
    if over_refunded_credit_memos:
        exceptions.append({
            "type": "over_refunded_credit_memo",
            "message": f"Customer refunds exceed available customer credit on credit memos: {over_refunded_credit_memos[:5]}.",
        })

    inventory = opening_inventory_map(context)
    events: list[tuple[pd.Timestamp, int, int, float, str, int]] = []
    goods_receipt_headers = context.tables["GoodsReceipt"].set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index") if not context.tables["GoodsReceipt"].empty else {}
    for line in context.tables["GoodsReceiptLine"].itertuples(index=False):
        header = goods_receipt_headers.get(int(line.GoodsReceiptID))
        if header is None:
            continue
        events.append((pd.Timestamp(header["ReceiptDate"]), 0, int(line.ItemID), int(header["WarehouseID"]), float(line.QuantityReceived), int(line.GoodsReceiptLineID)))
    completion_headers = context.tables["ProductionCompletion"].set_index("ProductionCompletionID")[["CompletionDate", "WarehouseID"]].to_dict("index") if not context.tables["ProductionCompletion"].empty else {}
    for line in context.tables["ProductionCompletionLine"].itertuples(index=False):
        header = completion_headers.get(int(line.ProductionCompletionID))
        if header is None:
            continue
        events.append((pd.Timestamp(header["CompletionDate"]), 0, int(line.ItemID), int(header["WarehouseID"]), float(line.QuantityCompleted), int(line.ProductionCompletionLineID)))
    shipment_headers = shipments.set_index("ShipmentID")[["ShipmentDate", "WarehouseID"]].to_dict("index") if not shipments.empty else {}
    for line in shipment_lines.itertuples(index=False):
        header = shipment_headers.get(int(line.ShipmentID))
        if header is None:
            continue
        events.append((pd.Timestamp(header["ShipmentDate"]), 1, int(line.ItemID), int(header["WarehouseID"]), float(line.QuantityShipped), int(line.ShipmentLineID)))
    sales_return_headers = sales_returns.set_index("SalesReturnID")[["ReturnDate", "WarehouseID"]].to_dict("index") if not sales_returns.empty else {}
    for line in sales_return_lines.itertuples(index=False):
        header = sales_return_headers.get(int(line.SalesReturnID))
        if header is None:
            continue
        events.append((pd.Timestamp(header["ReturnDate"]), 0, int(line.ItemID), int(header["WarehouseID"]), float(line.QuantityReturned), int(line.SalesReturnLineID)))
    for event_date, event_order, item_id, warehouse_id, quantity, source_id in sorted(events, key=lambda item: (item[0], item[1], item[5])):
        key = (int(item_id), int(warehouse_id))
        if event_order == 0:
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(quantity), 2)
            continue
        available = round(float(inventory.get(key, 0.0)), 2)
        if available < round(float(quantity), 2):
            exceptions.append({
                "type": "inventory_availability_breach",
                "shipment_line_id": int(source_id),
                "message": "Shipment consumes more inventory than available in the shadow inventory model.",
            })
        inventory[key] = round(available - float(quantity), 2)

    receivables_metrics = o2c_receivables_metrics(context)
    if float(receivables_metrics["trailing_twelve_month_sales"]) > 0 and float(receivables_metrics["implied_dso"]) > 90.0:
        exceptions.append({
            "type": "ar_dso_unrealistic",
            "message": "Open AR implies a DSO above the clean-build realism threshold.",
            "implied_dso": float(receivables_metrics["implied_dso"]),
        })
    if float(receivables_metrics["aging_90_plus_share"]) > 0.15:
        exceptions.append({
            "type": "ar_90_plus_share_excessive",
            "message": "90+ AR exceeds the clean-build realism threshold.",
            "aging_90_plus_share": float(receivables_metrics["aging_90_plus_share"]),
        })
    if float(receivables_metrics["aging_current_to_60_share"]) < 0.75:
        exceptions.append({
            "type": "ar_current_to_60_share_too_low",
            "message": "Current through 60-day AR does not dominate the clean-build aging profile.",
            "aging_current_to_60_share": float(receivables_metrics["aging_current_to_60_share"]),
        })
    stale_open_invoice_count = int(receivables_metrics["open_invoices_gt_365_count"])
    open_invoice_count = max(int(receivables_metrics["open_invoice_count"]), 1)
    if stale_open_invoice_count > max(5, int(open_invoice_count * 0.01)):
        exceptions.append({
            "type": "ar_old_invoices_excessive",
            "message": "Invoices older than one year remain open above the clean-build threshold.",
            "open_invoices_gt_365_count": stale_open_invoice_count,
        })

    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    year_end_dso_series: list[dict[str, float | int]] = []
    for year in range(fiscal_start.year, fiscal_end.year + 1):
        year_end = pd.Timestamp(year=year, month=12, day=31)
        if year_end < fiscal_start or year_end > fiscal_end:
            continue
        year_metrics = o2c_receivables_metrics(context, as_of_date=year_end)
        year_end_dso_series.append({
            "year": int(year),
            "implied_dso": float(year_metrics["implied_dso"]),
            "open_ar_amount": float(year_metrics["open_ar_amount"]),
        })
    if len(year_end_dso_series) >= 3:
        dso_values = [float(row["implied_dso"]) for row in year_end_dso_series]
        if all(later > earlier + 7.0 for earlier, later in zip(dso_values, dso_values[1:])) and dso_values[-1] > dso_values[0] + 35.0:
            exceptions.append({
                "type": "ar_dso_compounding",
                "message": "Year-end DSO compounds upward across the clean-build horizon.",
                "year_end_dso_series": year_end_dso_series,
            })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "open_state": o2c_open_state(context),
        "receivables_metrics": receivables_metrics,
        "year_end_dso_series": year_end_dso_series,
    }


def validate_phase6(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase5(context)
    exceptions = list(results["exceptions"])

    gl_balance = validate_gl_balance(context)
    if gl_balance["exception_count"]:
        exceptions.append(f"Unbalanced GL vouchers: {gl_balance['exception_count']}.")

    gl = context.tables["GLEntry"]
    trial_balance_difference = round(float(gl["Debit"].sum()) - float(gl["Credit"].sum()), 2)
    if trial_balance_difference != 0:
        exceptions.append(f"Trial balance is not balanced: {trial_balance_difference}.")

    rollforward = validate_account_rollforward(context)
    if rollforward["exception_count"]:
        exceptions.append(f"Control account roll-forward exceptions: {rollforward['exception_count']}.")

    phase6_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": gl_balance,
        "trial_balance_difference": trial_balance_difference,
        "account_rollforward": rollforward,
    }
    context.validation_results["phase6"] = phase6_results
    return phase6_results


def validate_phase7(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase6(context)
    exceptions = list(results["exceptions"])

    phase7_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "anomaly_count": len(context.anomaly_log),
    }
    context.validation_results["phase7"] = phase7_results
    return phase7_results


def fiscal_months(context: GenerationContext) -> list[tuple[int, int]]:
    start = pd.Timestamp(context.settings.fiscal_year_start)
    end = pd.Timestamp(context.settings.fiscal_year_end)
    months = pd.date_range(
        start=pd.Timestamp(year=start.year, month=start.month, day=1),
        end=pd.Timestamp(year=end.year, month=end.month, day=1),
        freq="MS",
    )
    return [(int(month.year), int(month.month)) for month in months]


def first_business_day(year: int, month: int) -> pd.Timestamp:
    day = pd.Timestamp(year=year, month=month, day=1)
    while day.day_name() in {"Saturday", "Sunday"}:
        day = day + pd.Timedelta(days=1)
    return day


def next_month(year: int, month: int) -> tuple[int, int]:
    current = pd.Timestamp(year=year, month=month, day=1) + pd.DateOffset(months=1)
    return int(current.year), int(current.month)


def journal_entry_type_amount_by_account(context: GenerationContext, entry_type: str, account_number: str) -> float:
    gl = context.tables["GLEntry"]
    journal_entries = context.tables["JournalEntry"]
    if gl.empty or journal_entries.empty:
        return 0.0

    account_id = account_id_by_number(context, account_number)
    journal_type_by_id = journal_entries.set_index("JournalEntryID")["EntryType"].to_dict()
    journal_gl = gl[
        gl["VoucherType"].eq("JournalEntry")
        & gl["SourceDocumentType"].eq("JournalEntry")
        & gl["SourceDocumentID"].notna()
        & gl["AccountID"].astype(int).eq(account_id)
    ].copy()
    if journal_gl.empty:
        return 0.0

    journal_gl["EntryType"] = journal_gl["SourceDocumentID"].astype(int).map(journal_type_by_id)
    matched = journal_gl[journal_gl["EntryType"].eq(entry_type)]
    return round(float(matched["Credit"].sum()) - float(matched["Debit"].sum()), 2)


def accrued_service_clear_amounts_by_journal(context: GenerationContext) -> dict[int, float]:
    accrual_amounts = {
        int(entry["JournalEntryID"]): float(entry["Amount"])
        for entry in accrual_journal_details(context)
    }
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty or "AccrualJournalEntryID" not in invoice_lines.columns:
        return {}

    cleared: dict[int, float] = {}
    for line in invoice_lines[invoice_lines["AccrualJournalEntryID"].notna()].sort_values(["PurchaseInvoiceID", "PILineID"]).itertuples(index=False):
        journal_entry_id = int(line.AccrualJournalEntryID)
        remaining = float(accrual_amounts.get(journal_entry_id, 0.0)) - float(cleared.get(journal_entry_id, 0.0))
        clear_amount = money(max(0.0, min(float(line.LineTotal), remaining)))
        cleared[journal_entry_id] = money(float(cleared.get(journal_entry_id, 0.0)) + clear_amount)
    return cleared


def accrued_adjustment_amounts_by_journal(context: GenerationContext) -> dict[int, float]:
    journal_entries = context.tables["JournalEntry"]
    gl = context.tables["GLEntry"]
    if journal_entries.empty or gl.empty:
        return {}

    adjustments = journal_entries[journal_entries["EntryType"].eq("Accrual Adjustment")]
    if adjustments.empty:
        return {}

    accrued_expenses_account_id = account_id_by_number(context, "2040")
    adjustment_amounts: dict[int, float] = {}
    for journal in adjustments.itertuples(index=False):
        if pd.isna(journal.ReversesJournalEntryID):
            continue
        linked_rows = gl[
            gl["SourceDocumentType"].eq("JournalEntry")
            & gl["SourceDocumentID"].notna()
            & gl["SourceDocumentID"].astype(int).eq(int(journal.JournalEntryID))
            & gl["AccountID"].astype(int).eq(accrued_expenses_account_id)
        ]
        adjustment_amounts[int(journal.ReversesJournalEntryID)] = money(
            float(adjustment_amounts.get(int(journal.ReversesJournalEntryID), 0.0)) + float(linked_rows["Debit"].sum())
        )
    return adjustment_amounts


def validate_journal_controls(context: GenerationContext) -> dict[str, Any]:
    journal_entries = context.tables["JournalEntry"]
    gl = context.tables["GLEntry"]
    journal_gl = gl[gl["SourceDocumentType"].eq("JournalEntry")].copy()
    gl_by_source = {int(source_id): rows for source_id, rows in journal_gl.groupby("SourceDocumentID")}
    exceptions: list[dict[str, Any]] = []

    for journal in journal_entries.itertuples(index=False):
        source_rows = gl_by_source.get(int(journal.JournalEntryID))
        if source_rows is None or len(source_rows) < 2:
            exceptions.append({
                "type": "missing_gl_rows",
                "journal_entry_id": int(journal.JournalEntryID),
                "message": "Journal entry does not have at least two linked GL rows.",
            })
            continue

        debit_total = round(float(source_rows["Debit"].sum()), 2)
        credit_total = round(float(source_rows["Credit"].sum()), 2)
        if debit_total != credit_total:
            exceptions.append({
                "type": "unbalanced_journal",
                "journal_entry_id": int(journal.JournalEntryID),
                "message": "Journal-linked GL rows are not balanced.",
            })
        if round(float(journal.TotalAmount), 2) != debit_total:
            exceptions.append({
                "type": "header_total_mismatch",
                "journal_entry_id": int(journal.JournalEntryID),
                "message": "Journal header total does not match debit total of linked GL rows.",
            })

    journal_lookup = journal_entries.set_index("JournalEntryID").to_dict("index")
    accrual_amounts = {
        int(entry["JournalEntryID"]): float(entry["Amount"])
        for entry in accrual_journal_details(context)
    }
    cleared_by_accrual = accrued_service_clear_amounts_by_journal(context)
    adjustment_totals = accrued_adjustment_amounts_by_journal(context)
    accrued_expenses_account_id = account_id_by_number(context, "2040")
    adjustments = journal_entries[journal_entries["EntryType"].eq("Accrual Adjustment")]
    for adjustment in adjustments.itertuples(index=False):
        reverses_id = adjustment.ReversesJournalEntryID
        if pd.isna(reverses_id):
            exceptions.append({
                "type": "missing_adjustment_link",
                "journal_entry_id": int(adjustment.JournalEntryID),
                "message": "Accrual adjustment is missing ReversesJournalEntryID.",
            })
            continue

        original = journal_lookup.get(int(reverses_id))
        if original is None or original["EntryType"] != "Accrual":
            exceptions.append({
                "type": "invalid_adjustment_link",
                "journal_entry_id": int(adjustment.JournalEntryID),
                "message": "Accrual adjustment does not reference a valid Accrual journal entry.",
            })
            continue

        if pd.Timestamp(adjustment.PostingDate) <= pd.Timestamp(original["PostingDate"]):
            exceptions.append({
                "type": "premature_adjustment",
                "journal_entry_id": int(adjustment.JournalEntryID),
                "message": "Accrual adjustment was posted on or before the original accrual date.",
            })
            continue

        source_rows = gl_by_source.get(int(adjustment.JournalEntryID))
        current_adjustment_amount = 0.0
        if source_rows is not None:
            current_adjustment_amount = round(
                float(
                    source_rows[
                        source_rows["AccountID"].astype(int).eq(accrued_expenses_account_id)
                    ]["Debit"].sum()
                ),
                2,
            )

        original_amount = float(accrual_amounts.get(int(reverses_id), 0.0))
        prior_adjustments = round(float(adjustment_totals.get(int(reverses_id), 0.0)) - current_adjustment_amount, 2)
        remaining_before_adjustment = round(
            original_amount
            - float(cleared_by_accrual.get(int(reverses_id), 0.0))
            - prior_adjustments,
            2,
        )
        if current_adjustment_amount <= 0:
            exceptions.append({
                "type": "empty_adjustment",
                "journal_entry_id": int(adjustment.JournalEntryID),
                "message": "Accrual adjustment does not debit accrued expenses.",
            })
        elif current_adjustment_amount >= remaining_before_adjustment:
            exceptions.append({
                "type": "full_or_excess_adjustment",
                "journal_entry_id": int(adjustment.JournalEntryID),
                "message": "Accrual adjustment is not partial or exceeds remaining accrued balance.",
            })

    fiscal_years = range(
        pd.Timestamp(context.settings.fiscal_year_start).year,
        pd.Timestamp(context.settings.fiscal_year_end).year + 1,
    )
    for year in fiscal_years:
        year_entries = journal_entries[pd.to_datetime(journal_entries["PostingDate"]).dt.year.eq(year)]
        pnl_close_count = int(year_entries["EntryType"].eq("Year-End Close - P&L to Income Summary").sum())
        re_close_count = int(year_entries["EntryType"].eq("Year-End Close - Income Summary to Retained Earnings").sum())
        if pnl_close_count != 1 or re_close_count != 1:
            exceptions.append({
                "type": "year_end_close_count",
                "fiscal_year": int(year),
                "message": "Fiscal year does not contain exactly two year-end close journal headers.",
            })

    expected_entry_counts = {
        "Rent": len(fiscal_months(context)) * 2,
        "Utilities": len(fiscal_months(context)),
        "Factory Overhead": sum(
            1 for year, month in fiscal_months(context) if monthly_factory_overhead_amount(context, year, month) > 0
        ),
        "Direct Labor Reclass": sum(
            1 for year, month in fiscal_months(context) if monthly_direct_labor_reclass_amount(context, year, month) > 0
        ),
        "Manufacturing Overhead Reclass": sum(
            1 for year, month in fiscal_months(context) if monthly_manufacturing_overhead_pool_amount(context, year, month) > 0
        ),
        "Depreciation": len(fiscal_months(context)) * 3,
        "Accrual": len(fiscal_months(context)) * len(ACCRUAL_ACCOUNT_METADATA),
        "Accrual Reversal": 0,
        "Year-End Close - P&L to Income Summary": len(list(fiscal_years)),
        "Year-End Close - Income Summary to Retained Earnings": len(list(fiscal_years)),
    }
    actual_entry_counts = journal_entries["EntryType"].value_counts().to_dict()
    for entry_type, expected_count in expected_entry_counts.items():
        actual_count = int(actual_entry_counts.get(entry_type, 0))
        if actual_count != expected_count:
            exceptions.append({
                "type": "entry_type_count",
                "entry_type": entry_type,
                "message": f"Expected {expected_count} journal entries of type {entry_type}, found {actual_count}.",
            })

    accounts = context.tables["Account"]
    pl_account_ids = accounts[
        accounts["AccountType"].isin(["Revenue", "Expense"])
        & accounts["AccountSubType"].ne("Header")
    ]["AccountID"].astype(int).tolist()
    income_summary_id = account_id_by_number(context, "8010")
    for year in fiscal_years:
        year_gl = gl[gl["FiscalYear"].astype(int).eq(int(year))]
        net_balances = year_gl.groupby("AccountID")[["Debit", "Credit"]].sum()
        non_zero_accounts = []
        for account_id in pl_account_ids + [income_summary_id]:
            if int(account_id) not in net_balances.index:
                continue
            difference = round(
                float(net_balances.loc[int(account_id), "Debit"]) - float(net_balances.loc[int(account_id), "Credit"]),
                2,
            )
            if difference != 0:
                non_zero_accounts.append(int(account_id))
        if non_zero_accounts:
            exceptions.append({
                "type": "unclosed_profit_and_loss",
                "fiscal_year": int(year),
                "message": f"Revenue, expense, or income summary accounts remain open after closing: {non_zero_accounts[:5]}.",
            })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "entry_type_counts": {key: int(value) for key, value in actual_entry_counts.items()},
    }


def validate_manufacturing_controls(context: GenerationContext) -> dict[str, Any]:
    exceptions: list[dict[str, Any]] = []
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    items = context.tables["Item"]
    boms = context.tables["BillOfMaterial"]
    bom_lines = context.tables["BillOfMaterialLine"]
    work_orders = context.tables["WorkOrder"]
    material_issues = context.tables["MaterialIssue"]
    material_issue_lines = context.tables["MaterialIssueLine"]
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    closes = context.tables["WorkOrderClose"]
    gl = context.tables["GLEntry"]
    work_order_operations = context.tables["WorkOrderOperation"]
    work_order_operation_schedule = context.tables["WorkOrderOperationSchedule"]

    manufactured_items = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ]
    purchased_items = items[
        items["SupplyMode"].eq("Purchased")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ]

    active_bom_counts = boms[boms["Status"].eq("Active")]["ParentItemID"].astype(int).value_counts()
    missing_boms = sorted(
        set(manufactured_items["ItemID"].astype(int)) - set(active_bom_counts.index.astype(int))
    )
    duplicate_boms = sorted(active_bom_counts[active_bom_counts.ne(1)].index.astype(int).tolist())
    if missing_boms:
        exceptions.append({
            "type": "manufactured_item_missing_bom",
            "message": f"Manufactured items are missing an active BOM: {missing_boms[:5]}.",
        })
    if duplicate_boms:
        exceptions.append({
            "type": "manufactured_item_duplicate_bom",
            "message": f"Manufactured items have more than one active BOM: {duplicate_boms[:5]}.",
        })

    purchased_boms = sorted(
        set(purchased_items["ItemID"].astype(int)) & set(active_bom_counts.index.astype(int))
    )
    if purchased_boms:
        exceptions.append({
            "type": "purchased_item_has_bom",
            "message": f"Purchased finished goods should not have active BOMs: {purchased_boms[:5]}.",
        })

    item_lookup = items.set_index("ItemID").to_dict("index") if not items.empty else {}
    for bom in boms.itertuples(index=False):
        parent = item_lookup.get(int(bom.ParentItemID))
        if parent is None or pd.isna(parent.get("RevenueAccountID")):
            exceptions.append({
                "type": "invalid_bom_parent",
                "message": f"BOM parent is not a sellable finished good: {int(bom.ParentItemID)}.",
            })

    bom_lookup = boms.set_index("BOMID").to_dict("index") if not boms.empty else {}
    for line in bom_lines.itertuples(index=False):
        component = item_lookup.get(int(line.ComponentItemID))
        if component is None or str(component.get("ItemGroup")) not in {"Raw Materials", "Packaging"}:
            exceptions.append({
                "type": "invalid_bom_component",
                "message": f"BOM component must be raw materials or packaging: {int(line.ComponentItemID)}.",
            })

    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index") if not work_orders.empty else {}
    completion_qty_map = work_order_completed_quantity_map(context)
    scheduled_work_orders = scheduled_work_order_ids(context)
    work_order_item_supply_modes = work_orders["ItemID"].astype(int).map(
        items.set_index("ItemID")["SupplyMode"].to_dict()
    ) if not work_orders.empty else pd.Series(dtype=object)
    if not work_orders.empty and work_order_item_supply_modes.ne("Manufactured").any():
        invalid_work_orders = work_orders.loc[work_order_item_supply_modes.ne("Manufactured"), "WorkOrderID"].astype(int).tolist()
        exceptions.append({
            "type": "work_order_non_manufactured_item",
            "message": f"Work orders exist for non-manufactured items: {invalid_work_orders[:5]}.",
        })

    if not work_orders.empty:
        over_completed = [
            int(work_order.WorkOrderID)
            for work_order in work_orders.itertuples(index=False)
            if round(float(completion_qty_map.get(int(work_order.WorkOrderID), 0.0)), 2) > round(float(work_order.PlannedQuantity), 2)
        ]
        if over_completed:
            exceptions.append({
                "type": "work_order_over_completed",
                "message": f"Work orders complete above planned quantity: {over_completed[:5]}.",
            })

        released_without_schedule = work_orders[
            work_orders["Status"].eq("Released")
            & ~work_orders["WorkOrderID"].astype(int).isin(scheduled_work_orders)
        ]
        for row in released_without_schedule.head(10).itertuples(index=False):
            exceptions.append({
                "type": "released_work_order_without_schedule",
                "message": f"Released work order {int(row.WorkOrderID)} has no operation schedule rows.",
            })

        schedule_bounds = work_order_schedule_bounds(context)
        actual_start_by_work_order: dict[int, pd.Timestamp] = {}
        if not work_order_operations.empty:
            started_operations = work_order_operations[
                work_order_operations["ActualStartDate"].notna()
            ].copy()
            if not started_operations.empty:
                started_operations["ActualStartDateTS"] = pd.to_datetime(
                    started_operations["ActualStartDate"],
                    errors="coerce",
                )
                actual_start_by_work_order = (
                    started_operations.dropna(subset=["ActualStartDateTS"])
                    .groupby("WorkOrderID")["ActualStartDateTS"]
                    .min()
                    .to_dict()
                )
        for row in work_orders.itertuples(index=False):
            bounds = schedule_bounds.get(int(row.WorkOrderID))
            if bounds is None or pd.isna(row.DueDate):
                continue
            if pd.Timestamp(bounds[1]) > pd.Timestamp(row.DueDate):
                exceptions.append({
                    "type": "work_order_scheduled_after_due_date",
                    "message": f"Work order {int(row.WorkOrderID)} schedules beyond its due date.",
                })
                if len(exceptions) >= 250:
                    break

            if str(row.Status) != "Released":
                continue

            first_scheduled = pd.Timestamp(bounds[0])
            released_date = pd.Timestamp(row.ReleasedDate) if pd.notna(row.ReleasedDate) else None
            if released_date is not None and first_scheduled > released_date + pd.Timedelta(days=45):
                exceptions.append({
                    "type": "released_work_order_far_ahead_of_schedule",
                    "message": f"Released work order {int(row.WorkOrderID)} is more than 45 days ahead of first scheduled activity.",
                })
                if len(exceptions) >= 250:
                    break

            due_date = pd.Timestamp(row.DueDate).normalize()
            actual_start = actual_start_by_work_order.get(int(row.WorkOrderID))
            if (
                actual_start is None
                and released_date is not None
                and due_date <= fiscal_end
                and released_date <= fiscal_end - pd.Timedelta(days=30)
            ):
                exceptions.append({
                    "type": "released_work_order_due_without_actual_start",
                    "message": f"Released work order {int(row.WorkOrderID)} is due within the fiscal year but still has no actual start.",
                })
                if len(exceptions) >= 250:
                    break

    if not work_order_operations.empty:
        scheduled_operation_ids = (
            set(work_order_operation_schedule["WorkOrderOperationID"].astype(int).tolist())
            if not work_order_operation_schedule.empty
            else set()
        )
        fiscal_end_text = pd.Timestamp(context.settings.fiscal_year_end).strftime("%Y-%m-%d")
        invalid_unscheduled_operations = work_order_operations[
            ~work_order_operations["WorkOrderOperationID"].astype(int).isin(scheduled_operation_ids)
            & (
                work_order_operations["PlannedStartDate"].astype(str).eq(fiscal_end_text)
                | work_order_operations["PlannedEndDate"].astype(str).eq(fiscal_end_text)
            )
        ]
        for row in invalid_unscheduled_operations.head(10).itertuples(index=False):
            exceptions.append({
                "type": "unscheduled_operation_fiscal_end_fallback",
                "message": f"Work-order operation {int(row.WorkOrderOperationID)} still uses a fiscal-year-end scheduling fallback.",
            })

    issue_header_lookup = material_issues.set_index("MaterialIssueID").to_dict("index") if not material_issues.empty else {}
    bom_line_lookup = bom_lines.set_index("BOMLineID").to_dict("index") if not bom_lines.empty else {}
    issue_qty_by_work_order_line: dict[tuple[int, int], float] = defaultdict(float)
    for line in material_issue_lines.itertuples(index=False):
        issue_header = issue_header_lookup.get(int(line.MaterialIssueID))
        bom_line = bom_line_lookup.get(int(line.BOMLineID))
        if issue_header is None or bom_line is None:
            exceptions.append({
                "type": "material_issue_invalid_reference",
                "message": f"Material issue line {int(line.MaterialIssueLineID)} has an invalid header or BOM line.",
            })
            continue
        work_order = work_order_lookup.get(int(issue_header["WorkOrderID"]))
        if work_order is None or int(work_order["BOMID"]) != int(bom_line["BOMID"]) or int(line.ItemID) != int(bom_line["ComponentItemID"]):
            exceptions.append({
                "type": "material_issue_bom_mismatch",
                "message": f"Material issue line {int(line.MaterialIssueLineID)} does not match its work-order BOM.",
            })
            continue
        issue_qty_by_work_order_line[(int(issue_header["WorkOrderID"]), int(line.BOMLineID))] += float(line.QuantityIssued)

    for (work_order_id, bom_line_id), issued_quantity in issue_qty_by_work_order_line.items():
        work_order = work_order_lookup.get(int(work_order_id))
        bom_line = bom_line_lookup.get(int(bom_line_id))
        if work_order is None or bom_line is None:
            continue
        planned_quantity = float(work_order["PlannedQuantity"])
        allowed_quantity = qty(
            planned_quantity
            * float(bom_line["QuantityPerUnit"])
            * (1 + float(bom_line["ScrapFactorPct"]))
            * 1.10
        )
        if round(float(issued_quantity), 2) > round(float(allowed_quantity), 2):
            exceptions.append({
                "type": "material_issue_exceeds_allowed_quantity",
                "message": f"Material issue quantity exceeds planned BOM quantity plus tolerance for work order {work_order_id}.",
            })

    completion_header_lookup = completions.set_index("ProductionCompletionID").to_dict("index") if not completions.empty else {}
    final_activity_dates: dict[int, pd.Timestamp] = {}
    for issue in material_issues.itertuples(index=False):
        final_activity_dates[int(issue.WorkOrderID)] = max(
            final_activity_dates.get(int(issue.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(issue.IssueDate),
        )
    for completion in completions.itertuples(index=False):
        final_activity_dates[int(completion.WorkOrderID)] = max(
            final_activity_dates.get(int(completion.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(completion.CompletionDate),
        )
    for close in closes.itertuples(index=False):
        if pd.Timestamp(close.CloseDate) < final_activity_dates.get(int(close.WorkOrderID), pd.Timestamp.min):
            exceptions.append({
                "type": "work_order_close_before_final_activity",
                "message": f"Work order close occurs before the final issue or completion for work order {int(close.WorkOrderID)}.",
            })

    inventory = {
        (item_id, warehouse_id): float(quantity)
        for (item_id, warehouse_id), quantity in opening_inventory_map(context).items()
        if str(item_lookup.get(int(item_id), {}).get("ItemGroup")) in {"Raw Materials", "Packaging"}
    }
    events: list[tuple[pd.Timestamp, int, pd.Timestamp, int, int, float, int]] = []
    goods_receipt_headers = context.tables["GoodsReceipt"].set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index") if not context.tables["GoodsReceipt"].empty else {}
    for line in context.tables["GoodsReceiptLine"].itertuples(index=False):
        header = goods_receipt_headers.get(int(line.GoodsReceiptID))
        if header is None or str(item_lookup.get(int(line.ItemID), {}).get("ItemGroup")) not in {"Raw Materials", "Packaging"}:
            continue
        receipt_date = pd.Timestamp(header["ReceiptDate"])
        month_start = pd.Timestamp(year=receipt_date.year, month=receipt_date.month, day=1)
        events.append((
            month_start,
            0,
            receipt_date,
            int(line.ItemID),
            int(header["WarehouseID"]),
            float(line.QuantityReceived),
            int(line.GoodsReceiptLineID),
        ))
    for line in material_issue_lines.itertuples(index=False):
        header = issue_header_lookup.get(int(line.MaterialIssueID))
        if header is None or str(item_lookup.get(int(line.ItemID), {}).get("ItemGroup")) not in {"Raw Materials", "Packaging"}:
            continue
        issue_date = pd.Timestamp(header["IssueDate"])
        month_start = pd.Timestamp(year=issue_date.year, month=issue_date.month, day=1)
        events.append((
            month_start,
            1,
            issue_date,
            int(line.ItemID),
            int(header["WarehouseID"]),
            float(line.QuantityIssued),
            int(line.MaterialIssueLineID),
        ))

    for _, event_order, event_date, item_id, warehouse_id, quantity, source_id in sorted(
        events,
        key=lambda item: (item[0], item[1], item[2], item[6]),
    ):
        key = (int(item_id), int(warehouse_id))
        if event_order == 0:
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(quantity), 2)
            continue
        available = round(float(inventory.get(key, 0.0)), 2)
        if available < round(float(quantity), 2):
            exceptions.append({
                "type": "negative_inventory_shadow",
                "message": f"Inventory goes negative for item {item_id} in warehouse {warehouse_id} at source {source_id}.",
            })
        inventory[key] = round(available - float(quantity), 2)

    operational_gl = gl[~gl["SourceDocumentType"].eq("JournalEntry")].copy()

    def gl_debit_net(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = operational_gl[operational_gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Debit"].sum()) - float(account_rows["Credit"].sum()), 2)

    def gl_debit_net_all(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = gl[gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Debit"].sum()) - float(account_rows["Credit"].sum()), 2)

    expected_wip = round(
        float(context.tables["MaterialIssueLine"]["ExtendedStandardCost"].sum())
        - float(context.tables["ProductionCompletionLine"]["ExtendedStandardMaterialCost"].sum())
        - float(context.tables["WorkOrderClose"]["MaterialVarianceAmount"].sum()),
        2,
    )
    if abs(round(expected_wip - gl_debit_net("1046"), 2)) > 0.01:
        exceptions.append({
            "type": "wip_rollforward_mismatch",
            "message": "WIP roll-forward does not reconcile to the ledger.",
        })

    expected_clearing = round(
        float(sum(work_order_actual_conversion_cost_map(context).values()))
        - float(context.tables["ProductionCompletionLine"]["ExtendedStandardConversionCost"].sum())
        - float(context.tables["WorkOrderClose"]["ConversionVarianceAmount"].sum()),
        2,
    )
    if abs(round(expected_clearing - gl_debit_net_all("1090"), 2)) > 0.01:
        exceptions.append({
            "type": "manufacturing_clearing_mismatch",
            "message": "Manufacturing conversion clearing roll-forward does not reconcile to the ledger.",
        })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "open_state": manufacturing_open_state(context),
    }


def validate_routing_controls(context: GenerationContext) -> dict[str, Any]:
    items = context.tables["Item"]
    routings = context.tables["Routing"]
    routing_operations = context.tables["RoutingOperation"]
    work_centers = context.tables["WorkCenter"]
    work_orders = context.tables["WorkOrder"]
    work_order_operations = context.tables["WorkOrderOperation"]
    exceptions: list[dict[str, Any]] = []

    if items.empty:
        return {"exception_count": 0, "exceptions": []}

    manufactured_items = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ].copy()
    purchased_items = items[
        items["SupplyMode"].ne("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ].copy()
    active_routings = active_routing_by_item(context)

    missing_routings = sorted(
        set(manufactured_items["ItemID"].astype(int)) - set(active_routings.keys())
    )
    duplicate_routing_counts = (
        routings[routings["Status"].eq("Active")]["ParentItemID"].astype(int).value_counts()
        if not routings.empty
        else pd.Series(dtype=int)
    )
    duplicate_routings = sorted(duplicate_routing_counts[duplicate_routing_counts.ne(1)].index.astype(int).tolist())
    purchased_routings = sorted(
        set(purchased_items["ItemID"].astype(int)) & set(active_routings.keys())
    )
    if missing_routings:
        exceptions.append({
            "type": "manufactured_item_missing_routing",
            "message": f"Manufactured items are missing an active routing: {missing_routings[:5]}.",
        })
    if duplicate_routings:
        exceptions.append({
            "type": "manufactured_item_duplicate_routing",
            "message": f"Manufactured items have more than one active routing: {duplicate_routings[:5]}.",
        })
    if purchased_routings:
        exceptions.append({
            "type": "purchased_item_has_routing",
            "message": f"Purchased items should not have active routings: {purchased_routings[:5]}.",
        })

    item_lookup = items.set_index("ItemID").to_dict("index")
    for routing in routings.itertuples(index=False):
        parent = item_lookup.get(int(routing.ParentItemID))
        if parent is None or str(parent.get("SupplyMode")) != "Manufactured" or pd.isna(parent.get("RevenueAccountID")):
            exceptions.append({
                "type": "invalid_routing_parent",
                "message": f"Routing parent is not a manufactured sellable item: {int(routing.ParentItemID)}.",
            })

    work_center_ids = set(work_centers["WorkCenterID"].astype(int).tolist()) if not work_centers.empty else set()
    routing_operation_groups = routing_operations_by_routing(context)
    for routing_id, rows in routing_operation_groups.items():
        sequences = rows["OperationSequence"].astype(int).tolist()
        if sequences != list(range(1, len(sequences) + 1)):
            exceptions.append({
                "type": "routing_sequence_gap",
                "message": f"Routing {routing_id} has non-contiguous operation sequences.",
            })
        if rows["OperationSequence"].astype(int).duplicated().any():
            exceptions.append({
                "type": "routing_sequence_duplicate",
                "message": f"Routing {routing_id} has duplicate operation sequences.",
            })
        invalid_work_centers = sorted(set(rows["WorkCenterID"].astype(int)) - work_center_ids)
        if invalid_work_centers:
            exceptions.append({
                "type": "routing_invalid_work_center",
                "message": f"Routing {routing_id} references invalid work centers: {invalid_work_centers[:5]}.",
            })

    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index") if not work_orders.empty else {}
    work_order_operation_groups = work_order_operations_by_work_order(context)
    manufactured_work_orders = work_orders[
        work_orders["ItemID"].astype(int).isin(manufactured_items["ItemID"].astype(int))
    ] if not work_orders.empty else work_orders.head(0)
    for work_order in manufactured_work_orders.itertuples(index=False):
        rows = work_order_operation_groups.get(int(work_order.WorkOrderID))
        if rows is None or rows.empty:
            exceptions.append({
                "type": "work_order_missing_operations",
                "message": f"Work order {int(work_order.WorkOrderID)} is missing work-order operations.",
            })
            continue
        if rows["RoutingOperationID"].isna().any():
            exceptions.append({
                "type": "work_order_operation_missing_routing_operation",
                "message": f"Work order {int(work_order.WorkOrderID)} has operation rows without routing linkage.",
            })
        prior_completion: pd.Timestamp | None = None
        for row in rows.itertuples(index=False):
            actual_start = pd.Timestamp(row.ActualStartDate) if pd.notna(row.ActualStartDate) else None
            actual_end = pd.Timestamp(row.ActualEndDate) if pd.notna(row.ActualEndDate) else None
            if prior_completion is not None and actual_start is not None and actual_start < prior_completion:
                exceptions.append({
                    "type": "work_order_operation_out_of_sequence",
                    "message": f"Work-order operation sequence is violated for work order {int(work_order.WorkOrderID)}.",
                })
                break
            if actual_end is not None:
                prior_completion = actual_end

        final_actual_end = None
        if rows["ActualEndDate"].notna().any():
            final_actual_end = pd.to_datetime(rows["ActualEndDate"]).max()
        if final_actual_end is not None and pd.notna(work_order.CompletedDate):
            if pd.Timestamp(work_order.CompletedDate) < pd.Timestamp(final_actual_end):
                exceptions.append({
                    "type": "work_order_completed_before_final_operation",
                    "message": f"Work order {int(work_order.WorkOrderID)} completes before the final routing operation ends.",
                })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_capacity_controls(context: GenerationContext) -> dict[str, Any]:
    work_centers = context.tables["WorkCenter"]
    work_center_calendar = context.tables["WorkCenterCalendar"]
    work_order_operations = context.tables["WorkOrderOperation"]
    work_order_operation_schedule = context.tables["WorkOrderOperationSchedule"]
    material_issues = context.tables["MaterialIssue"]
    production_completions = context.tables["ProductionCompletion"]
    work_order_closes = context.tables["WorkOrderClose"]
    exceptions: list[dict[str, Any]] = []

    if work_centers.empty:
        return {
            "exception_count": 0,
            "exceptions": [],
            "capacity_state": manufacturing_capacity_state(context, pd.Timestamp(context.settings.fiscal_year_end).year, pd.Timestamp(context.settings.fiscal_year_end).month),
        }

    expected_dates = set(context.calendar["Date"].astype(str).tolist())
    work_center_ids = set(work_centers["WorkCenterID"].astype(int).tolist())
    expected_count = len(expected_dates) * len(work_center_ids)

    if len(work_center_calendar) != expected_count:
        exceptions.append({
            "type": "work_center_calendar_coverage",
            "message": f"Expected {expected_count} work-center calendar rows, found {len(work_center_calendar)}.",
        })

    if not work_center_calendar.empty:
        invalid_reasons = sorted(
            set(work_center_calendar["ExceptionReason"].astype(str).tolist()) - set(CAPACITY_EXCEPTION_REASONS)
        )
        if invalid_reasons:
            exceptions.append({
                "type": "work_center_calendar_exception_reason",
                "message": f"Work-center calendar uses invalid exception reasons: {invalid_reasons[:5]}.",
            })

        grouped = work_center_calendar.groupby("WorkCenterID")["CalendarDate"].nunique()
        missing = [
            int(work_center_id)
            for work_center_id, date_count in grouped.items()
            if int(date_count) != len(expected_dates)
        ]
        if missing:
            exceptions.append({
                "type": "work_center_calendar_missing_dates",
                "message": f"Work centers are missing one or more calendar dates: {missing[:5]}.",
            })

        calendar_copy = work_center_calendar.copy()
        calendar_copy["CalendarDateTS"] = pd.to_datetime(calendar_copy["CalendarDate"], errors="coerce")
        invalid_nonworking = calendar_copy[
            (
                calendar_copy["IsWorkingDay"].astype(int).eq(0)
                | calendar_copy["ExceptionReason"].isin(["Weekend", "Holiday"])
            )
            & calendar_copy["AvailableHours"].astype(float).ne(0.0)
        ]
        if not invalid_nonworking.empty:
            exceptions.append({
                "type": "calendar_nonworking_available_hours",
                "message": "Non-working work-center calendar days must have zero available hours.",
            })

    schedule_by_operation = work_order_operation_schedule_by_operation(context)
    calendar_lookup = (
        work_center_calendar.set_index(["WorkCenterID", "CalendarDate"]).to_dict("index")
        if not work_center_calendar.empty
        else {}
    )
    operation_lookup = (
        work_order_operations.set_index("WorkOrderOperationID").to_dict("index")
        if not work_order_operations.empty
        else {}
    )

    if not work_order_operation_schedule.empty:
        invalid_schedule_refs = []
        for row in work_order_operation_schedule.itertuples(index=False):
            operation = operation_lookup.get(int(row.WorkOrderOperationID))
            if operation is None:
                invalid_schedule_refs.append(int(row.WorkOrderOperationScheduleID))
                continue
            if int(operation["WorkCenterID"]) != int(row.WorkCenterID):
                invalid_schedule_refs.append(int(row.WorkOrderOperationScheduleID))
        if invalid_schedule_refs:
            exceptions.append({
                "type": "invalid_schedule_reference",
                "message": f"Schedule rows reference invalid operations or work centers: {invalid_schedule_refs[:5]}.",
            })

        schedule_by_day = (
            work_order_operation_schedule.groupby(["WorkCenterID", "ScheduleDate"])["ScheduledHours"].sum().round(2)
        )
        for (work_center_id, schedule_date), scheduled_hours in schedule_by_day.items():
            calendar_row = calendar_lookup.get((int(work_center_id), str(schedule_date)))
            available_hours = float(calendar_row["AvailableHours"]) if calendar_row is not None else 0.0
            if round(float(scheduled_hours), 2) > round(available_hours, 2):
                exceptions.append({
                    "type": "work_center_day_overbooked",
                    "work_center_id": int(work_center_id),
                    "schedule_date": str(schedule_date),
                    "message": "Scheduled hours exceed available capacity for the work-center day.",
                })
            if calendar_row is not None and int(calendar_row["IsWorkingDay"]) == 0 and round(float(scheduled_hours), 2) > 0:
                exceptions.append({
                    "type": "scheduled_on_nonworking_day",
                    "work_center_id": int(work_center_id),
                    "schedule_date": str(schedule_date),
                    "message": "Work-order operation was scheduled on a non-working calendar day.",
                })

    for row in work_order_operations.itertuples(index=False):
        schedule_rows = schedule_by_operation.get(int(row.WorkOrderOperationID))
        horizon_exhausted = str(row.PlannedEndDate) == str(context.settings.fiscal_year_end)
        if schedule_rows is None or schedule_rows.empty:
            if not horizon_exhausted:
                exceptions.append({
                    "type": "missing_operation_schedule",
                    "message": f"Work-order operation {int(row.WorkOrderOperationID)} is missing schedule rows.",
                })
            continue
        scheduled_hours = round(float(schedule_rows["ScheduledHours"].astype(float).sum()), 2)
        if scheduled_hours != round(float(row.PlannedLoadHours), 2) and not horizon_exhausted:
            exceptions.append({
                "type": "planned_load_mismatch",
                "message": f"Scheduled hours do not equal planned load for work-order operation {int(row.WorkOrderOperationID)}.",
            })
        if str(schedule_rows["ScheduleDate"].min()) != str(row.PlannedStartDate) or str(schedule_rows["ScheduleDate"].max()) != str(row.PlannedEndDate):
            exceptions.append({
                "type": "planned_window_mismatch",
                "message": f"Planned dates do not match schedule rows for work-order operation {int(row.WorkOrderOperationID)}.",
            })

    work_order_groups = work_order_operations_by_work_order(context)
    issue_dates_by_work_order = (
        material_issues.groupby("WorkOrderID")["IssueDate"].min().to_dict()
        if not material_issues.empty
        else {}
    )
    completion_dates_by_work_order = (
        production_completions.groupby("WorkOrderID")["CompletionDate"].max().to_dict()
        if not production_completions.empty
        else {}
    )
    close_dates_by_work_order = (
        work_order_closes.groupby("WorkOrderID")["CloseDate"].max().to_dict()
        if not work_order_closes.empty
        else {}
    )

    for work_order_id, rows in work_order_groups.items():
        prior_planned_end: pd.Timestamp | None = None
        final_actual_end: pd.Timestamp | None = None
        first_planned_start: pd.Timestamp | None = None
        for row in rows.itertuples(index=False):
            planned_start = pd.Timestamp(row.PlannedStartDate) if pd.notna(row.PlannedStartDate) else None
            planned_end = pd.Timestamp(row.PlannedEndDate) if pd.notna(row.PlannedEndDate) else None
            actual_end = pd.Timestamp(row.ActualEndDate) if pd.notna(row.ActualEndDate) else None
            if first_planned_start is None and planned_start is not None:
                first_planned_start = planned_start
            if prior_planned_end is not None and planned_start is not None and planned_start < prior_planned_end:
                exceptions.append({
                    "type": "planned_operation_sequence_violation",
                    "message": f"Planned operation sequence is violated for work order {int(work_order_id)}.",
                })
                break
            if planned_end is not None:
                prior_planned_end = planned_end
            if actual_end is not None:
                final_actual_end = actual_end

        issue_date = issue_dates_by_work_order.get(int(work_order_id))
        if issue_date is not None and first_planned_start is not None and pd.Timestamp(issue_date) < first_planned_start:
            exceptions.append({
                "type": "issue_before_first_scheduled_operation",
                "message": f"Material issue precedes first scheduled operation for work order {int(work_order_id)}.",
            })

        completion_date = completion_dates_by_work_order.get(int(work_order_id))
        if completion_date is not None and final_actual_end is not None and pd.Timestamp(completion_date) < final_actual_end:
            exceptions.append({
                "type": "completion_before_operation_end",
                "message": f"Production completion precedes final operation end for work order {int(work_order_id)}.",
            })

        close_date = close_dates_by_work_order.get(int(work_order_id))
        if close_date is not None:
            comparison_dates = [pd.Timestamp(value) for value in [issue_date, completion_date] if value is not None]
            if final_actual_end is not None:
                comparison_dates.append(pd.Timestamp(final_actual_end))
            if comparison_dates and pd.Timestamp(close_date) < max(comparison_dates):
                exceptions.append({
                    "type": "work_order_close_before_final_activity",
                    "message": f"Work-order close precedes final activity for work order {int(work_order_id)}.",
                })

    end_timestamp = pd.Timestamp(context.settings.fiscal_year_end)
    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "capacity_state": manufacturing_capacity_state(context, int(end_timestamp.year), int(end_timestamp.month)),
    }


def validate_payroll_controls(context: GenerationContext) -> dict[str, Any]:
    periods = context.tables["PayrollPeriod"]
    labor_entries = context.tables["LaborTimeEntry"]
    completions = context.tables["ProductionCompletion"]
    registers = context.tables["PayrollRegister"]
    register_lines = context.tables["PayrollRegisterLine"]
    payments = context.tables["PayrollPayment"]
    remittances = context.tables["PayrollLiabilityRemittance"]
    employees = context.tables["Employee"]
    work_orders = context.tables["WorkOrder"]
    work_order_operations = context.tables["WorkOrderOperation"]
    routing_operations = context.tables["RoutingOperation"]
    items = context.tables["Item"]
    exceptions: list[dict[str, Any]] = []

    if not periods.empty:
        ordered_periods = periods.sort_values("PayrollPeriodID").reset_index(drop=True)
        processed_periods = ordered_periods[ordered_periods["Status"].eq("Processed")].reset_index(drop=True)
        prior_end: pd.Timestamp | None = None
        for period in processed_periods.itertuples(index=False):
            period_start = pd.Timestamp(period.PeriodStartDate)
            period_end = pd.Timestamp(period.PeriodEndDate)
            if prior_end is not None and period_start != prior_end + pd.Timedelta(days=1):
                exceptions.append({
                    "type": "payroll_period_gap_or_overlap",
                    "message": "Payroll periods are not continuous and non-overlapping.",
                })
                break
            prior_end = period_end

        active_count_by_period: dict[int, int] = {}
        if not employees.empty:
            employee_hires = pd.to_datetime(employees["HireDate"])
            employee_terminations = pd.to_datetime(employees["TerminationDate"], errors="coerce")
            for period in processed_periods.itertuples(index=False):
                period_end = pd.Timestamp(period.PeriodEndDate)
                pay_date = pd.Timestamp(period.PayDate)
                active_count_by_period[int(period.PayrollPeriodID)] = int(
                    (
                        employee_hires.le(period_end)
                        & (employee_terminations.isna() | employee_terminations.ge(pay_date))
                    ).sum()
                )
        register_count_by_period = registers.groupby("PayrollPeriodID").size().to_dict() if not registers.empty else {}
        for payroll_period_id, expected_count in active_count_by_period.items():
            actual_count = int(register_count_by_period.get(int(payroll_period_id), 0))
            if actual_count != expected_count:
                exceptions.append({
                    "type": "missing_payroll_registers",
                    "payroll_period_id": int(payroll_period_id),
                    "message": f"Expected {expected_count} payroll registers, found {actual_count}.",
                })

    if not registers.empty and not register_lines.empty:
        line_groups = {key: value for key, value in register_lines.groupby("PayrollRegisterID")}
        for register in registers.itertuples(index=False):
            lines = line_groups.get(int(register.PayrollRegisterID))
            if lines is None or lines.empty:
                exceptions.append({
                    "type": "payroll_register_missing_lines",
                    "payroll_register_id": int(register.PayrollRegisterID),
                    "message": "Payroll register has no lines.",
                })
                continue
            earnings_total = float(lines.loc[lines["LineType"].isin(["Regular Earnings", "Overtime Earnings", "Salary Earnings", "Bonus"]), "Amount"].astype(float).sum())
            if round(earnings_total, 2) != round(float(register.GrossPay), 2):
                exceptions.append({
                    "type": "payroll_gross_mismatch",
                    "payroll_register_id": int(register.PayrollRegisterID),
                    "message": "Payroll register gross pay does not match earnings lines.",
                })
            withholding_total = float(lines.loc[lines["LineType"].isin(["Employee Tax Withholding", "Benefits Deduction"]), "Amount"].astype(float).sum())
            if round(withholding_total, 2) != round(float(register.EmployeeWithholdings), 2):
                exceptions.append({
                    "type": "payroll_withholding_mismatch",
                    "payroll_register_id": int(register.PayrollRegisterID),
                    "message": "Payroll register withholdings do not match line detail.",
                })
            if round(float(register.NetPay), 2) != round(float(register.GrossPay) - float(register.EmployeeWithholdings), 2):
                exceptions.append({
                    "type": "payroll_net_pay_formula",
                    "payroll_register_id": int(register.PayrollRegisterID),
                    "message": "Payroll register net pay does not equal gross pay minus employee withholdings.",
                })

    if not payments.empty and not registers.empty:
        register_ids = set(registers["PayrollRegisterID"].astype(int))
        payment_register_ids = set(payments["PayrollRegisterID"].astype(int))
        missing_payments = sorted(register_ids - payment_register_ids)
        if missing_payments:
            exceptions.append({
                "type": "missing_payroll_payments",
                "message": f"Payroll registers are missing payroll payments: {missing_payments[:5]}.",
            })

    remitted_amounts = payroll_liability_remitted_amounts(context)
    recorded_amounts = payroll_liability_recorded_amounts(context)
    for account_number in ["2031", "2032", "2033"]:
        if round(float(remitted_amounts.get(account_number, 0.0)), 2) > round(float(recorded_amounts.get(account_number, 0.0)), 2):
            exceptions.append({
                "type": "payroll_remittance_exceeds_recorded",
                "account_number": account_number,
                "message": f"Payroll remittances exceed recorded liability for account {account_number}.",
            })

    if not labor_entries.empty and not work_orders.empty and not items.empty:
        work_order_item_ids = work_orders.set_index("WorkOrderID")["ItemID"].astype(int).to_dict()
        supply_modes = items.set_index("ItemID")["SupplyMode"].to_dict()
        operation_lookup = work_order_operations.set_index("WorkOrderOperationID").to_dict("index") if not work_order_operations.empty else {}
        routing_operation_lookup = routing_operations.set_index("RoutingOperationID").to_dict("index") if not routing_operations.empty else {}
        invalid_direct_labor = []
        invalid_operation_links = []
        missing_operation_links = []
        for entry in labor_entries.itertuples(index=False):
            if str(entry.LaborType) != "Direct Manufacturing" or pd.isna(entry.WorkOrderID):
                continue
            item_id = work_order_item_ids.get(int(entry.WorkOrderID))
            if item_id is None or str(supply_modes.get(int(item_id))) != "Manufactured":
                invalid_direct_labor.append(int(entry.LaborTimeEntryID))
            if pd.isna(entry.WorkOrderOperationID):
                if not work_order_operations.empty:
                    missing_operation_links.append(int(entry.LaborTimeEntryID))
                continue
            operation = operation_lookup.get(int(entry.WorkOrderOperationID))
            routing_operation = None
            if operation is not None:
                routing_operation = routing_operation_lookup.get(int(operation["RoutingOperationID"]))
            if (
                operation is None
                or int(operation["WorkOrderID"]) != int(entry.WorkOrderID)
                or routing_operation is None
                or str(routing_operation.get("OperationCode")) not in {"ASSEMBLY", "FINISH", "QA", "CUT", "PACK"}
            ):
                invalid_operation_links.append(int(entry.LaborTimeEntryID))
        if invalid_direct_labor:
            exceptions.append({
                "type": "direct_labor_invalid_work_order",
                "message": f"Direct labor entries reference invalid or non-manufactured work orders: {invalid_direct_labor[:5]}.",
            })
        if missing_operation_links:
            exceptions.append({
                "type": "direct_labor_missing_operation",
                "message": f"Direct labor entries are missing work-order operation linkage: {missing_operation_links[:5]}.",
            })
        if invalid_operation_links:
            exceptions.append({
                "type": "direct_labor_invalid_operation_link",
                "message": f"Direct labor entries reference invalid work-order operations: {invalid_operation_links[:5]}.",
            })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_time_clock_controls(context: GenerationContext) -> dict[str, Any]:
    employees = context.tables["Employee"]
    time_clocks = context.tables["TimeClockEntry"]
    labor_entries = context.tables["LaborTimeEntry"]
    registers = context.tables["PayrollRegister"]
    register_lines = context.tables["PayrollRegisterLine"]
    work_orders = context.tables["WorkOrder"]
    work_order_operations = context.tables["WorkOrderOperation"]
    completions = context.tables["ProductionCompletion"]
    payroll_periods = context.tables["PayrollPeriod"]
    shift_definitions = context.tables["ShiftDefinition"]
    exceptions: list[dict[str, Any]] = []

    if employees.empty:
        return {"exception_count": 0, "exceptions": []}

    employee_lookup = employees.set_index("EmployeeID").to_dict("index")
    hourly_employee_ids = set(
        employees.loc[employees["PayClass"].eq("Hourly"), "EmployeeID"].astype(int).tolist()
    )
    salary_employee_ids = set(
        employees.loc[employees["PayClass"].eq("Salary"), "EmployeeID"].astype(int).tolist()
    )
    shift_lookup = shift_definitions.set_index("ShiftDefinitionID").to_dict("index") if not shift_definitions.empty else {}
    roster_lookup = employee_shift_roster_lookup(context)
    time_clock_lookup = time_clock_entry_lookup(context)
    labor_lookup = labor_entries.set_index("LaborTimeEntryID").to_dict("index") if not labor_entries.empty else {}
    labor_rows_by_time_clock: dict[int, list[dict[str, Any]]] = defaultdict(list)
    if not labor_entries.empty:
        for labor_row in labor_entries.to_dict(orient="records"):
            time_clock_id = labor_row.get("TimeClockEntryID")
            if pd.notna(time_clock_id):
                labor_rows_by_time_clock[int(time_clock_id)].append(labor_row)
    earliest_direct_labor_date_by_work_order: dict[int, pd.Timestamp] = {}
    if not labor_entries.empty:
        direct_labor = labor_entries[
            labor_entries["LaborType"].eq("Direct Manufacturing")
            & labor_entries["WorkOrderID"].notna()
            & labor_entries["WorkDate"].notna()
        ].copy()
        if not direct_labor.empty:
            direct_labor["WorkDateTS"] = pd.to_datetime(direct_labor["WorkDate"], errors="coerce")
            direct_labor = direct_labor[direct_labor["WorkDateTS"].notna()].copy()
            if not direct_labor.empty:
                earliest_direct_labor_date_by_work_order = {
                    int(work_order_id): pd.Timestamp(work_date)
                    for work_order_id, work_date in direct_labor.groupby("WorkOrderID")["WorkDateTS"].min().items()
                }
    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index") if not work_orders.empty else {}
    operation_lookup = work_order_operations.set_index("WorkOrderOperationID").to_dict("index") if not work_order_operations.empty else {}
    payroll_period_lookup = payroll_periods.set_index("PayrollPeriodID").to_dict("index") if not payroll_periods.empty else {}
    completion_work_order_period_pairs: set[tuple[int, int]] = set()
    if not completions.empty and payroll_period_lookup:
        ordered_periods = [
            (
                int(payroll_period_id),
                pd.Timestamp(period["PeriodStartDate"]),
                pd.Timestamp(period["PeriodEndDate"]),
            )
            for payroll_period_id, period in payroll_period_lookup.items()
        ]
        for completion in completions.itertuples(index=False):
            completion_date = pd.Timestamp(completion.CompletionDate)
            for payroll_period_id, period_start, period_end in ordered_periods:
                if period_start <= completion_date <= period_end:
                    completion_work_order_period_pairs.add((int(completion.WorkOrderID), int(payroll_period_id)))
                    break

    if not time_clocks.empty:
        duplicate_day_rows = (
            time_clocks.groupby(["EmployeeID", "WorkDate"]).size().reset_index(name="RowCount")
        )
        duplicate_day_rows = duplicate_day_rows[duplicate_day_rows["RowCount"].gt(1)]
        if not duplicate_day_rows.empty:
            exceptions.append({
                "type": "duplicate_time_clock_day",
                "message": f"Duplicate time-clock days found: {duplicate_day_rows.head(5).to_dict(orient='records')}.",
            })

        for row in time_clocks.itertuples(index=False):
            employee_id = int(row.EmployeeID)
            if employee_id in salary_employee_ids:
                exceptions.append({
                    "type": "salary_employee_time_clock",
                    "time_clock_entry_id": int(row.TimeClockEntryID),
                    "message": f"Salaried employee {employee_id} has a routine time-clock entry.",
                })

            if row.ClockOutTime is None or pd.isna(row.ClockOutTime):
                exceptions.append({
                    "type": "missing_clock_out",
                    "time_clock_entry_id": int(row.TimeClockEntryID),
                    "message": f"Time-clock entry {int(row.TimeClockEntryID)} is missing ClockOutTime.",
                })
                continue

            total_minutes = (
                pd.Timestamp(row.ClockOutTime) - pd.Timestamp(row.ClockInTime)
            ).total_seconds() / 60.0
            span_hours = round(max(total_minutes - float(row.BreakMinutes), 0.0) / 60.0, 2)
            expected_hours = round(float(row.RegularHours) + float(row.OvertimeHours), 2)
            if abs(span_hours - expected_hours) > 0.02:
                exceptions.append({
                    "type": "time_clock_span_mismatch",
                    "time_clock_entry_id": int(row.TimeClockEntryID),
                    "message": f"Time-clock span {span_hours} does not match recorded hours {expected_hours}.",
                })

            shift_definition = shift_lookup.get(int(row.ShiftDefinitionID)) if pd.notna(row.ShiftDefinitionID) else None
            roster = roster_lookup.get(int(row.EmployeeShiftRosterID)) if pd.notna(row.EmployeeShiftRosterID) else None
            if roster is not None:
                shift_start = pd.Timestamp(f"{row.WorkDate} {roster['ScheduledStartTime']}")
                shift_end = pd.Timestamp(f"{row.WorkDate} {roster['ScheduledEndTime']}")
            elif shift_definition is not None:
                shift_start = pd.Timestamp(f"{row.WorkDate} {shift_definition['StartTime']}")
                shift_end = pd.Timestamp(f"{row.WorkDate} {shift_definition['EndTime']}")
            else:
                shift_start = None
                shift_end = None
            if shift_start is not None and shift_end is not None:
                clock_in = pd.Timestamp(row.ClockInTime)
                clock_out = pd.Timestamp(row.ClockOutTime)
                if abs((clock_in - shift_start).total_seconds() / 60.0) > 45:
                    exceptions.append({
                        "type": "off_shift_clock_in",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Clock-in time falls materially outside the assigned shift for entry {int(row.TimeClockEntryID)}.",
                    })
                if clock_out < shift_start or clock_out > shift_end + pd.Timedelta(hours=4):
                    exceptions.append({
                        "type": "off_shift_clock_out",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Clock-out time falls materially outside the assigned shift for entry {int(row.TimeClockEntryID)}.",
                    })

            if pd.notna(row.WorkOrderOperationID):
                operation = operation_lookup.get(int(row.WorkOrderOperationID))
                if operation is None:
                    exceptions.append({
                        "type": "invalid_operation_link",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Time-clock entry {int(row.TimeClockEntryID)} references a missing work-order operation.",
                    })
                    continue
                if pd.notna(row.WorkOrderID) and int(operation["WorkOrderID"]) != int(row.WorkOrderID):
                    exceptions.append({
                        "type": "time_clock_work_order_mismatch",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Time-clock entry {int(row.TimeClockEntryID)} links to an operation outside its work order.",
                    })
                if pd.notna(row.WorkCenterID) and int(operation["WorkCenterID"]) != int(row.WorkCenterID):
                    exceptions.append({
                        "type": "time_clock_work_center_mismatch",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Time-clock entry {int(row.TimeClockEntryID)} links to an operation outside its work center.",
                    })
                work_date = pd.Timestamp(row.WorkDate)
                lower_bound = pd.Timestamp(operation["ActualStartDate"]) if pd.notna(operation["ActualStartDate"]) else pd.Timestamp(operation["PlannedStartDate"])
                upper_bound = pd.Timestamp(operation["ActualEndDate"]) if pd.notna(operation["ActualEndDate"]) else pd.Timestamp(operation["PlannedEndDate"])
                direct_labor_rows = [
                    labor_row
                    for labor_row in labor_rows_by_time_clock.get(int(row.TimeClockEntryID), [])
                    if str(labor_row.get("LaborType")) == "Direct Manufacturing"
                ]
                post_completion_fallback = False
                work_order = work_order_lookup.get(int(operation["WorkOrderID"]))
                payroll_period = payroll_period_lookup.get(int(row.PayrollPeriodID)) if pd.notna(row.PayrollPeriodID) else None
                if (
                    payroll_period is not None
                    and (int(operation["WorkOrderID"]), int(row.PayrollPeriodID)) in completion_work_order_period_pairs
                    and direct_labor_rows
                ):
                    period_end = pd.Timestamp(payroll_period["PeriodEndDate"])
                    post_completion_fallback = work_date <= period_end
                elif (
                    work_order is not None
                    and payroll_period is not None
                    and pd.notna(work_order.get("CompletedDate"))
                    and direct_labor_rows
                ):
                    completed_date = pd.Timestamp(work_order["CompletedDate"])
                    period_start = pd.Timestamp(payroll_period["PeriodStartDate"])
                    period_end = pd.Timestamp(payroll_period["PeriodEndDate"])
                    post_completion_fallback = (
                        period_start <= completed_date <= period_end
                        and completed_date <= work_date <= period_end
                    )
                if (
                    not post_completion_fallback
                    and
                    work_order is not None
                    and payroll_period is not None
                    and pd.notna(work_order.get("CompletedDate"))
                    and direct_labor_rows
                ):
                    completed_date = pd.Timestamp(work_order["CompletedDate"])
                    period_start = pd.Timestamp(payroll_period["PeriodStartDate"])
                    period_end = pd.Timestamp(payroll_period["PeriodEndDate"])
                    earliest_direct_labor_date = earliest_direct_labor_date_by_work_order.get(int(operation["WorkOrderID"]))
                    post_completion_fallback = (
                        earliest_direct_labor_date is not None
                        and period_start <= earliest_direct_labor_date <= period_end
                        and completed_date <= work_date <= period_end
                    )
                if (work_date < lower_bound or work_date > upper_bound) and not post_completion_fallback:
                    exceptions.append({
                        "type": "time_clock_outside_operation_window",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Time-clock entry {int(row.TimeClockEntryID)} falls outside the operation window.",
                    })
                if work_order is not None and pd.notna(work_order.get("ClosedDate")) and work_date > pd.Timestamp(work_order["ClosedDate"]):
                    exceptions.append({
                        "type": "labor_after_work_order_close",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Time-clock entry {int(row.TimeClockEntryID)} occurs after work-order close.",
                    })

    if not registers.empty and not register_lines.empty:
        hourly_registers = registers[registers["EmployeeID"].astype(int).isin(hourly_employee_ids)].copy()
        approved_hours = approved_time_clock_hours_by_employee_period(context)
        earnings_lines = register_lines[
            register_lines["LineType"].isin(["Regular Earnings", "Overtime Earnings"])
        ].copy()
        hourly_register_lookup = hourly_registers.set_index("PayrollRegisterID").to_dict("index")
        for line in earnings_lines.itertuples(index=False):
            register = hourly_register_lookup.get(int(line.PayrollRegisterID))
            if register is None:
                continue
            if pd.isna(line.LaborTimeEntryID):
                exceptions.append({
                    "type": "hourly_pay_without_labor_entry",
                    "payroll_register_line_id": int(line.PayrollRegisterLineID),
                    "message": f"Hourly payroll line {int(line.PayrollRegisterLineID)} is missing LaborTimeEntryID.",
                })
                continue
            labor_entry = labor_lookup.get(int(line.LaborTimeEntryID))
            if labor_entry is None:
                exceptions.append({
                    "type": "hourly_pay_missing_labor_entry",
                    "payroll_register_line_id": int(line.PayrollRegisterLineID),
                    "message": f"Hourly payroll line {int(line.PayrollRegisterLineID)} references a missing labor entry.",
                })
                continue
            time_clock_id = labor_entry.get("TimeClockEntryID")
            if pd.isna(time_clock_id):
                exceptions.append({
                    "type": "paid_without_clock",
                    "payroll_register_line_id": int(line.PayrollRegisterLineID),
                    "message": f"Hourly payroll line {int(line.PayrollRegisterLineID)} does not trace to a time-clock entry.",
                })
                continue
            time_clock = time_clock_lookup.get(int(time_clock_id))
            if time_clock is None or str(time_clock.get("ClockStatus")) != "Approved":
                exceptions.append({
                    "type": "paid_without_approved_clock",
                    "payroll_register_line_id": int(line.PayrollRegisterLineID),
                    "message": f"Hourly payroll line {int(line.PayrollRegisterLineID)} does not trace to an approved time clock.",
                })
                continue
            line_hours = round(float(line.Hours or 0.0), 2)
            if str(line.LineType) == "Regular Earnings":
                entry_hours = round(float(labor_entry["RegularHours"]), 2)
            else:
                entry_hours = round(float(labor_entry["OvertimeHours"]), 2)
            if line_hours != entry_hours:
                exceptions.append({
                    "type": "payroll_line_hours_mismatch",
                    "payroll_register_line_id": int(line.PayrollRegisterLineID),
                    "message": f"Payroll hours {line_hours} do not match labor-entry hours {entry_hours}.",
                })

        for register in hourly_registers.itertuples(index=False):
            if round(float(register.GrossPay), 2) <= 0:
                continue
            approved_total = float(approved_hours.get((int(register.EmployeeID), int(register.PayrollPeriodID)), 0.0))
            if round(approved_total, 2) <= 0:
                exceptions.append({
                    "type": "hourly_register_without_clock_coverage",
                    "payroll_register_id": int(register.PayrollRegisterID),
                    "message": f"Hourly payroll register {int(register.PayrollRegisterID)} has pay but no approved time-clock coverage.",
                })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_workforce_planning_controls(context: GenerationContext) -> dict[str, Any]:
    employees = context.tables["Employee"]
    assignments = context.tables["EmployeeShiftAssignment"]
    rosters = context.tables["EmployeeShiftRoster"]
    absences = context.tables["EmployeeAbsence"]
    time_clocks = context.tables["TimeClockEntry"]
    punches = context.tables["TimeClockPunch"]
    work_center_calendar = context.tables["WorkCenterCalendar"]
    exceptions: list[dict[str, Any]] = []

    if employees.empty or rosters.empty:
        return {"exception_count": 0, "exceptions": []}

    employee_lookup = employees.set_index("EmployeeID").to_dict("index")
    roster_lookup = employee_shift_roster_lookup(context)
    overtime_lookup = overtime_approval_lookup(context)
    punches_by_entry = time_clock_punches_by_entry(context)
    assignments_by_employee: dict[int, list[dict[str, Any]]] = defaultdict(list)
    if not assignments.empty:
        for row in assignments.sort_values(["EmployeeID", "EffectiveStartDate", "EmployeeShiftAssignmentID"]).to_dict(orient="records"):
            assignments_by_employee[int(row["EmployeeID"])].append(row)
    calendar_lookup: dict[tuple[int, str], dict[str, Any]] = {}
    if not work_center_calendar.empty:
        calendar_lookup = {
            (int(row.WorkCenterID), str(row.CalendarDate)): row._asdict()
            for row in work_center_calendar.itertuples(index=False)
        }

    absent_roster_ids = set()
    for roster in rosters.itertuples(index=False):
        roster_id = int(roster.EmployeeShiftRosterID)
        employee_id = int(roster.EmployeeID)
        work_date = pd.Timestamp(roster.RosterDate)
        employee = employee_lookup.get(employee_id)
        if employee is None:
            exceptions.append({
                "type": "roster_missing_employee",
                "employee_shift_roster_id": roster_id,
                "message": f"Shift roster {roster_id} references a missing employee.",
            })
            continue
        if str(employee["PayClass"]) != "Hourly":
            exceptions.append({
                "type": "salary_employee_roster",
                "employee_shift_roster_id": roster_id,
                "message": f"Shift roster {roster_id} was generated for salaried employee {employee_id}.",
            })
        hire_date = pd.Timestamp(employee["HireDate"])
        termination_date = pd.Timestamp(employee["TerminationDate"]) if pd.notna(employee["TerminationDate"]) else None
        if work_date < hire_date or (termination_date is not None and work_date > termination_date):
            exceptions.append({
                "type": "roster_outside_employment_dates",
                "employee_shift_roster_id": roster_id,
                "message": f"Shift roster {roster_id} falls outside employee {employee_id} employment dates.",
            })
        matching_assignment = None
        for assignment in assignments_by_employee.get(employee_id, []):
            start_date = pd.Timestamp(assignment["EffectiveStartDate"])
            end_date = pd.Timestamp(assignment["EffectiveEndDate"])
            if start_date <= work_date <= end_date:
                matching_assignment = assignment
                break
        if matching_assignment is None:
            exceptions.append({
                "type": "roster_outside_shift_assignment",
                "employee_shift_roster_id": roster_id,
                "message": f"Shift roster {roster_id} falls outside the employee shift-assignment range.",
            })
        if pd.notna(roster.WorkCenterID):
            calendar_row = calendar_lookup.get((int(roster.WorkCenterID), str(roster.RosterDate)))
            if calendar_row is None or int(calendar_row["IsWorkingDay"]) != 1:
                exceptions.append({
                    "type": "roster_on_nonworking_day",
                    "employee_shift_roster_id": roster_id,
                    "message": f"Shift roster {roster_id} falls on a non-working day for work center {int(roster.WorkCenterID)}.",
                })
        if str(roster.RosterStatus) == "Absent":
            absent_roster_ids.add(roster_id)

    for absence in absences.itertuples(index=False):
        employee = employee_lookup.get(int(absence.EmployeeID))
        roster = roster_lookup.get(int(absence.EmployeeShiftRosterID)) if pd.notna(absence.EmployeeShiftRosterID) else None
        if employee is None or roster is None:
            exceptions.append({
                "type": "absence_missing_roster_or_employee",
                "employee_absence_id": int(absence.EmployeeAbsenceID),
                "message": f"Employee absence {int(absence.EmployeeAbsenceID)} is missing a valid roster or employee link.",
            })
            continue
        if int(roster["EmployeeID"]) != int(absence.EmployeeID) or str(roster["RosterDate"]) != str(absence.AbsenceDate):
            exceptions.append({
                "type": "absence_roster_mismatch",
                "employee_absence_id": int(absence.EmployeeAbsenceID),
                "message": f"Employee absence {int(absence.EmployeeAbsenceID)} does not match its linked roster row.",
            })

    if not punches.empty:
        grouped = punches.sort_values(["EmployeeID", "WorkDate", "SequenceNumber", "TimeClockPunchID"]).groupby(["EmployeeID", "WorkDate"])
        for (employee_id, work_date), group in grouped:
            sequence = group["SequenceNumber"].astype(int).tolist()
            if sequence != list(range(1, len(sequence) + 1)):
                exceptions.append({
                    "type": "noncontiguous_punch_sequence",
                    "employee_id": int(employee_id),
                    "work_date": str(work_date),
                    "message": f"Punch sequence for employee {int(employee_id)} on {work_date} is not contiguous.",
                })
            timestamps = pd.to_datetime(group["PunchTimestamp"], errors="coerce")
            if timestamps.isna().any() or not timestamps.is_monotonic_increasing:
                exceptions.append({
                    "type": "invalid_punch_order",
                    "employee_id": int(employee_id),
                    "work_date": str(work_date),
                    "message": f"Punch timestamps for employee {int(employee_id)} on {work_date} are invalid or out of order.",
                })
            punch_types = group.sort_values("SequenceNumber")["PunchType"].astype(str).tolist()
            if punch_types not in (["Clock In", "Clock Out"], ["Clock In", "Meal Start", "Meal End", "Clock Out"]):
                exceptions.append({
                    "type": "invalid_punch_pattern",
                    "employee_id": int(employee_id),
                    "work_date": str(work_date),
                    "message": f"Punch pattern for employee {int(employee_id)} on {work_date} is invalid: {punch_types}.",
                })
            roster_ids = group["EmployeeShiftRosterID"].dropna().astype(int).unique().tolist()
            if not roster_ids:
                exceptions.append({
                    "type": "punch_without_roster",
                    "employee_id": int(employee_id),
                    "work_date": str(work_date),
                    "message": f"Punches exist for employee {int(employee_id)} on {work_date} without a linked roster row.",
                })

    for row in time_clocks.itertuples(index=False):
        roster_id = None if pd.isna(row.EmployeeShiftRosterID) else int(row.EmployeeShiftRosterID)
        roster = roster_lookup.get(roster_id) if roster_id is not None else None
        if roster is None:
            exceptions.append({
                "type": "time_clock_missing_roster",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not link to a valid shift roster row.",
            })
            continue
        if int(roster["EmployeeID"]) != int(row.EmployeeID) or str(roster["RosterDate"]) != str(row.WorkDate):
            exceptions.append({
                "type": "time_clock_roster_mismatch",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not match its linked shift roster row.",
            })
        recorded_hours = round(float(row.RegularHours) + float(row.OvertimeHours), 2)
        scheduled_hours = round(float(roster["ScheduledHours"]), 2)
        if recorded_hours > scheduled_hours + 0.02 and pd.isna(row.OvertimeApprovalID):
            exceptions.append({
                "type": "overtime_without_approval",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} exceeds rostered hours without overtime approval.",
            })
        if pd.notna(row.OvertimeApprovalID):
            approval = overtime_lookup.get(int(row.OvertimeApprovalID))
            if approval is None:
                exceptions.append({
                    "type": "missing_overtime_approval",
                    "time_clock_entry_id": int(row.TimeClockEntryID),
                    "message": f"Time-clock entry {int(row.TimeClockEntryID)} references a missing overtime approval.",
                })
            else:
                if int(approval["EmployeeID"]) != int(row.EmployeeID) or str(approval["WorkDate"]) != str(row.WorkDate):
                    exceptions.append({
                        "type": "overtime_approval_mismatch",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Overtime approval {int(row.OvertimeApprovalID)} does not match the employee/date on time-clock entry {int(row.TimeClockEntryID)}.",
                    })
                if float(approval["ApprovedHours"]) + 0.02 < float(row.OvertimeHours):
                    exceptions.append({
                        "type": "insufficient_overtime_approval_hours",
                        "time_clock_entry_id": int(row.TimeClockEntryID),
                        "message": f"Overtime approval {int(row.OvertimeApprovalID)} is below recorded overtime hours on entry {int(row.TimeClockEntryID)}.",
                    })
        punch_rows = punches_by_entry.get(int(row.TimeClockEntryID), [])
        if not punch_rows:
            exceptions.append({
                "type": "time_clock_without_punches",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not reconcile to raw punch rows.",
            })
            continue
        ordered_punches = sorted(punch_rows, key=lambda item: (int(item["SequenceNumber"]), int(item["TimeClockPunchID"])))
        first_punch = ordered_punches[0]
        last_punch = ordered_punches[-1]
        if str(first_punch["PunchType"]) != "Clock In" or str(last_punch["PunchType"]) != "Clock Out":
            exceptions.append({
                "type": "time_clock_punch_boundary_mismatch",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not begin with Clock In and end with Clock Out punch types.",
            })
        if str(first_punch["PunchTimestamp"]) != str(row.ClockInTime) or str(last_punch["PunchTimestamp"]) != str(row.ClockOutTime):
            exceptions.append({
                "type": "time_clock_punch_timestamp_mismatch",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not reconcile to its first/last punch timestamps.",
            })
        meal_gap_minutes = 0.0
        for start_punch, end_punch in zip(ordered_punches, ordered_punches[1:], strict=False):
            if str(start_punch["PunchType"]) == "Meal Start" and str(end_punch["PunchType"]) == "Meal End":
                meal_gap_minutes += (
                    pd.Timestamp(end_punch["PunchTimestamp"]) - pd.Timestamp(start_punch["PunchTimestamp"])
                ).total_seconds() / 60.0
        if round(meal_gap_minutes, 2) != round(float(row.BreakMinutes), 2):
            exceptions.append({
                "type": "break_minutes_punch_mismatch",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Time-clock entry {int(row.TimeClockEntryID)} does not reconcile break minutes to meal punches.",
            })

    if absent_roster_ids:
        time_clock_roster_ids = pd.to_numeric(time_clocks["EmployeeShiftRosterID"], errors="coerce").astype("Int64")
        absent_time_clocks = time_clocks[
            time_clock_roster_ids.notna()
            & time_clock_roster_ids.isin(absent_roster_ids)
        ]
        for row in absent_time_clocks.head(20).itertuples(index=False):
            exceptions.append({
                "type": "absence_with_worked_time",
                "time_clock_entry_id": int(row.TimeClockEntryID),
                "message": f"Absent roster row {int(row.EmployeeShiftRosterID)} still has worked time.",
            })
        punch_roster_ids = pd.to_numeric(punches["EmployeeShiftRosterID"], errors="coerce").astype("Int64")
        absent_punches = punches[
            punch_roster_ids.notna()
            & punch_roster_ids.isin(absent_roster_ids)
        ]
        if not absent_punches.empty:
            for row in absent_punches.head(20).itertuples(index=False):
                exceptions.append({
                    "type": "absence_with_punches",
                    "time_clock_punch_id": int(row.TimeClockPunchID),
                    "message": f"Absent roster row {int(row.EmployeeShiftRosterID)} still has punch activity.",
                })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_planning_controls(context: GenerationContext) -> dict[str, Any]:
    items = context.tables["Item"]
    forecasts = context.tables["DemandForecast"]
    policies = context.tables["InventoryPolicy"]
    recommendations = context.tables["SupplyPlanRecommendation"]
    material_plans = context.tables["MaterialRequirementPlan"]
    rough_cut = context.tables["RoughCutCapacityPlan"]
    purchase_requisitions = context.tables["PurchaseRequisition"]
    work_orders = context.tables["WorkOrder"]
    work_center_calendar = context.tables["WorkCenterCalendar"]
    boms = context.tables["BillOfMaterial"]
    bom_lines = context.tables["BillOfMaterialLine"]
    exceptions: list[dict[str, Any]] = []

    if items.empty:
        return {"exception_count": 0, "exceptions": []}

    item_lookup = items.set_index("ItemID").to_dict("index")
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end)
    active_sellable_items = items[
        items["RevenueAccountID"].notna()
        & items["IsActive"].astype(int).eq(1)
        & items["LaunchDate"].notna()
    ].copy()

    if not forecasts.empty:
        forecasts = forecasts.copy()
        forecasts["WeekStartTS"] = pd.to_datetime(forecasts["ForecastWeekStartDate"], errors="coerce")
        forecasts["ItemIDNumeric"] = pd.to_numeric(forecasts["ItemID"], errors="coerce").astype("Int64")
        forecast_counts = (
            forecasts.dropna(subset=["ItemIDNumeric", "WeekStartTS"])
            .groupby("ItemIDNumeric")["WeekStartTS"]
            .nunique()
            .to_dict()
        )
        fiscal_start = pd.Timestamp(context.settings.fiscal_year_start)
        fiscal_end_week = planning_week_start(fiscal_end)
        for row in active_sellable_items.itertuples(index=False):
            launch_week = first_forecast_week_start(row.LaunchDate)
            effective_start = max(launch_week, planning_week_start(fiscal_start))
            expected_weeks = 0
            if effective_start <= fiscal_end_week:
                expected_weeks = int(((fiscal_end_week - effective_start).days // 7) + 1)
            actual_weeks = int(forecast_counts.get(int(row.ItemID), 0))
            if actual_weeks < expected_weeks:
                exceptions.append({
                    "type": "missing_forecast_coverage",
                    "item_id": int(row.ItemID),
                    "message": f"Item {int(row.ItemID)} is missing weekly forecast coverage after launch.",
                })
                if len(exceptions) >= 25:
                    break

        merged_forecasts = forecasts.merge(
            items[["ItemID", "LaunchDate", "LifecycleStatus", "IsActive"]],
            on="ItemID",
            how="left",
        )
        invalid_launch_rows = merged_forecasts[
            merged_forecasts["WeekStartTS"].lt(pd.to_datetime(merged_forecasts["LaunchDate"], errors="coerce"))
        ]
        for row in invalid_launch_rows.head(10).itertuples(index=False):
            exceptions.append({
                "type": "forecast_before_launch",
                "item_id": int(row.ItemID),
                "message": f"Forecast row exists before launch for item {int(row.ItemID)}.",
            })
        invalid_discontinued_rows = merged_forecasts[
            merged_forecasts["LifecycleStatus"].eq("Discontinued")
            & merged_forecasts["IsActive"].astype(int).ne(1)
            & merged_forecasts["ForecastQuantity"].astype(float).gt(0)
        ]
        for row in invalid_discontinued_rows.head(10).itertuples(index=False):
            exceptions.append({
                "type": "forecast_for_discontinued_item",
                "item_id": int(row.ItemID),
                "message": f"Inactive discontinued item {int(row.ItemID)} still has positive forecast demand.",
            })

    if not policies.empty:
        active_policies = policies[policies["IsActive"].astype(int).eq(1)].copy()
        duplicates = active_policies.groupby(["ItemID", "WarehouseID"]).size().reset_index(name="RowCount")
        duplicates = duplicates[duplicates["RowCount"].ne(1)]
        for row in duplicates.head(10).itertuples(index=False):
            exceptions.append({
                "type": "policy_uniqueness_failure",
                "item_id": int(row.ItemID),
                "warehouse_id": int(row.WarehouseID),
                "message": f"Expected exactly one active policy for item {int(row.ItemID)} warehouse {int(row.WarehouseID)}.",
            })

    recommendation_lookup = recommendations.set_index("SupplyPlanRecommendationID").to_dict("index") if not recommendations.empty else {}
    if not recommendations.empty:
        invalid_quantities = recommendations[
            recommendations["NetRequirementQuantity"].astype(float).lt(0)
            | recommendations["RecommendedOrderQuantity"].astype(float).lt(0)
        ]
        for row in invalid_quantities.head(10).itertuples(index=False):
            exceptions.append({
                "type": "negative_recommendation_quantity",
                "recommendation_id": int(row.SupplyPlanRecommendationID),
                "message": f"Recommendation {int(row.SupplyPlanRecommendationID)} has a negative planning quantity.",
            })

        release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
        recommended_quantities = pd.to_numeric(
            recommendations["RecommendedOrderQuantity"],
            errors="coerce",
        ).fillna(0.0)
        overdue_planned = recommendations[
            recommendations["RecommendationStatus"].eq("Planned")
            & release_dates.notna()
            & release_dates.le(fiscal_end)
            & recommended_quantities.gt(0)
        ].copy()
        for row in overdue_planned.head(10).itertuples(index=False):
            exceptions.append({
                "type": "overdue_planned_recommendation",
                "recommendation_id": int(row.SupplyPlanRecommendationID),
                "message": f"{str(row.RecommendationType)} recommendation {int(row.SupplyPlanRecommendationID)} remains planned after its release date.",
            })

        converted = recommendations[recommendations["RecommendationStatus"].eq("Converted")].copy()
        if not converted.empty:
            for row in converted.itertuples(index=False):
                if str(row.ConvertedDocumentType) == "PurchaseRequisition":
                    matches = purchase_requisitions[
                        purchase_requisitions["RequisitionID"].astype(int).eq(int(row.ConvertedDocumentID))
                    ]
                    if matches.empty or matches["SupplyPlanRecommendationID"].isna().all():
                        exceptions.append({
                            "type": "converted_requisition_link_failure",
                            "recommendation_id": int(row.SupplyPlanRecommendationID),
                            "message": f"Converted purchase recommendation {int(row.SupplyPlanRecommendationID)} does not reconcile to its requisition link.",
                        })
                    elif pd.Timestamp(matches.iloc[0]["RequestDate"]) > pd.Timestamp(row.NeedByDate):
                        exceptions.append({
                            "type": "late_requisition_conversion",
                            "recommendation_id": int(row.SupplyPlanRecommendationID),
                            "message": f"Purchase recommendation {int(row.SupplyPlanRecommendationID)} converted after need-by date.",
                        })
                if str(row.ConvertedDocumentType) == "WorkOrder":
                    matches = work_orders[
                        work_orders["WorkOrderID"].astype(int).eq(int(row.ConvertedDocumentID))
                    ]
                    if matches.empty or matches["SupplyPlanRecommendationID"].isna().all():
                        exceptions.append({
                            "type": "converted_work_order_link_failure",
                            "recommendation_id": int(row.SupplyPlanRecommendationID),
                            "message": f"Converted manufacturing recommendation {int(row.SupplyPlanRecommendationID)} does not reconcile to its work-order link.",
                        })
                    elif pd.Timestamp(matches.iloc[0]["ReleasedDate"]) > pd.Timestamp(row.NeedByDate):
                        exceptions.append({
                            "type": "late_work_order_conversion",
                            "recommendation_id": int(row.SupplyPlanRecommendationID),
                            "message": f"Manufacturing recommendation {int(row.SupplyPlanRecommendationID)} converted after need-by date.",
                        })

    if not material_plans.empty and not boms.empty and not bom_lines.empty:
        active_boms = boms[boms["Status"].eq("Active")].copy()
        bom_lookup = active_boms.set_index("ParentItemID")["BOMID"].astype(int).to_dict()
        bom_line_lookup = bom_lines.set_index("BOMLineID").to_dict("index")
        grouped_bom_lines = {
            int(bom_id): rows.copy()
            for bom_id, rows in bom_lines.groupby("BOMID")
        }
        for row in material_plans.head(len(material_plans)).itertuples(index=False):
            recommendation = recommendation_lookup.get(int(row.SupplyPlanRecommendationID))
            if recommendation is None:
                exceptions.append({
                    "type": "missing_parent_recommendation",
                    "material_requirement_plan_id": int(row.MaterialRequirementPlanID),
                    "message": f"MRP row {int(row.MaterialRequirementPlanID)} references a missing parent recommendation.",
                })
                continue
            bom_id = bom_lookup.get(int(row.ParentItemID))
            bom_rows = grouped_bom_lines.get(int(bom_id), pd.DataFrame()) if bom_id is not None else pd.DataFrame()
            expected_gross = None
            if not bom_rows.empty:
                match = bom_rows[bom_rows["ComponentItemID"].astype(int).eq(int(row.ComponentItemID))]
                if not match.empty:
                    bom_line = match.iloc[0]
                    expected_gross = qty(
                        float(recommendation["RecommendedOrderQuantity"])
                        * float(bom_line["QuantityPerUnit"])
                        * (1 + float(bom_line["ScrapFactorPct"]))
                    )
            if expected_gross is not None and round(float(row.GrossRequirementQuantity), 2) != round(float(expected_gross), 2):
                exceptions.append({
                    "type": "mrp_bom_quantity_mismatch",
                    "material_requirement_plan_id": int(row.MaterialRequirementPlanID),
                    "message": f"MRP row {int(row.MaterialRequirementPlanID)} does not reconcile to BOM quantity requirements.",
                })
                if len(exceptions) >= 250:
                    break

    if not rough_cut.empty and not work_center_calendar.empty:
        calendar = work_center_calendar.copy()
        calendar["WeekStart"] = pd.to_datetime(calendar["CalendarDate"], errors="coerce").map(planning_week_start)
        available_hours = calendar.groupby(["WeekStart", "WorkCenterID"])["AvailableHours"].sum().round(2)
        for row in rough_cut.head(len(rough_cut)).itertuples(index=False):
            expected_available = float(
                available_hours.get((pd.Timestamp(row.BucketWeekStartDate), int(row.WorkCenterID)), 0.0)
            )
            if round(float(row.AvailableHours), 2) != round(expected_available, 2):
                exceptions.append({
                    "type": "rough_cut_available_hours_mismatch",
                    "rough_cut_capacity_plan_id": int(row.RoughCutCapacityPlanID),
                    "message": f"Rough-cut capacity row {int(row.RoughCutCapacityPlanID)} does not reconcile to work-center calendar availability.",
                })
                if len(exceptions) >= 250:
                    break

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_pricing_controls(context: GenerationContext) -> dict[str, Any]:
    price_lists = context.tables["PriceList"]
    price_list_lines = context.tables["PriceListLine"]
    promotions = context.tables["PromotionProgram"]
    override_approvals = context.tables["PriceOverrideApproval"]
    items = context.tables["Item"]
    customers = context.tables["Customer"]
    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    credit_memo_lines = context.tables["CreditMemoLine"]
    exceptions: list[dict[str, Any]] = []

    def values_match(left: Any, right: Any, *, numeric: bool = False) -> bool:
        if pd.isna(left) and pd.isna(right):
            return True
        if numeric:
            return round(float(left), 4) == round(float(right), 4)
        return str(left) == str(right)

    if price_lists.empty or price_list_lines.empty:
        return {
            "exception_count": 1,
            "exceptions": [{
                "type": "missing_pricing_master_data",
                "message": "Price-list master data was not generated.",
            }],
        }

    active_sellable_items = items[
        items["IsActive"].astype(int).eq(1)
        & items["ListPrice"].notna()
        & items["RevenueAccountID"].notna()
        & items["ItemGroup"].ne("Services")
    ].copy()
    active_segment_lists = price_lists[
        price_lists["ScopeType"].eq("Segment")
        & price_lists["Status"].eq("Active")
        & price_lists["CustomerSegment"].isin(["Strategic", "Wholesale", "Design Trade", "Small Business"])
    ].copy()
    segment_lookup = active_segment_lists.groupby("CustomerSegment")["PriceListID"].apply(list).to_dict()
    active_line_keys = set(
        zip(
            price_list_lines["PriceListID"].astype(int),
            price_list_lines["ItemID"].astype(int),
        )
    )
    for item in active_sellable_items.head(len(active_sellable_items)).itertuples(index=False):
        for segment in ["Strategic", "Wholesale", "Design Trade", "Small Business"]:
            matching_lists = [int(price_list_id) for price_list_id in segment_lookup.get(segment, [])]
            if not matching_lists:
                exceptions.append({
                    "type": "missing_segment_price_list",
                    "customer_segment": segment,
                    "message": f"Missing active segment price list for {segment}.",
                })
                continue
            if not any((int(price_list_id), int(item.ItemID)) in active_line_keys for price_list_id in matching_lists):
                exceptions.append({
                    "type": "missing_price_list_item_coverage",
                    "item_id": int(item.ItemID),
                    "customer_segment": segment,
                    "message": f"Item {int(item.ItemID)} is missing active price-list coverage for segment {segment}.",
                })
        if len(exceptions) >= 50:
            break

    active_lists = price_lists[price_lists["Status"].eq("Active")].copy()
    if not active_lists.empty:
        active_lists["EffectiveStartTS"] = pd.to_datetime(active_lists["EffectiveStartDate"], errors="coerce")
        active_lists["EffectiveEndTS"] = pd.to_datetime(active_lists["EffectiveEndDate"], errors="coerce")
        grouped_lists = active_lists.groupby(["ScopeType", "CustomerID", "CustomerSegment"], dropna=False)
        for _, group in grouped_lists:
            sorted_group = group.sort_values(["EffectiveStartTS", "PriceListID"])
            prior_end = None
            prior_id = None
            for row in sorted_group.itertuples(index=False):
                if prior_end is not None and pd.notna(row.EffectiveStartTS) and pd.notna(prior_end) and pd.Timestamp(row.EffectiveStartTS) <= pd.Timestamp(prior_end):
                    exceptions.append({
                        "type": "overlapping_active_price_list",
                        "price_list_id": int(row.PriceListID),
                        "message": f"Active price list {int(row.PriceListID)} overlaps active price list {int(prior_id)} for the same pricing scope.",
                    })
                prior_end = row.EffectiveEndTS
                prior_id = int(row.PriceListID)

    line_break_duplicates = (
        price_list_lines.groupby(["PriceListID", "ItemID", "MinimumQuantity"]).size().reset_index(name="RowCount")
    )
    duplicate_breaks = line_break_duplicates[line_break_duplicates["RowCount"].gt(1)]
    for row in duplicate_breaks.head(10).itertuples(index=False):
        exceptions.append({
            "type": "overlapping_price_break",
            "price_list_id": int(row.PriceListID),
            "item_id": int(row.ItemID),
            "message": f"Price list {int(row.PriceListID)} item {int(row.ItemID)} has overlapping minimum-quantity breaks.",
        })

    promotion_lookup = promotions.set_index("PromotionID").to_dict("index") if not promotions.empty else {}
    order_lookup = sales_orders.set_index("SalesOrderID").to_dict("index") if not sales_orders.empty else {}
    customer_lookup = customers.set_index("CustomerID").to_dict("index") if not customers.empty else {}
    item_lookup = items.set_index("ItemID").to_dict("index") if not items.empty else {}
    for line in sales_order_lines[sales_order_lines["PromotionID"].notna()].itertuples(index=False):
        promotion = promotion_lookup.get(int(line.PromotionID))
        order = order_lookup.get(int(line.SalesOrderID))
        item = item_lookup.get(int(line.ItemID))
        customer = customer_lookup.get(int(order["CustomerID"])) if order is not None else None
        if promotion is None or order is None or item is None or customer is None:
            continue
        order_date = pd.Timestamp(order["OrderDate"])
        scope_type = str(promotion["ScopeType"])
        scope_valid = (
            (scope_type == "Segment" and str(customer["CustomerSegment"]) == str(promotion.get("CustomerSegment")))
            or (scope_type == "ItemGroup" and str(item["ItemGroup"]) == str(promotion.get("ItemGroup")))
            or (scope_type == "Collection" and str(item.get("CollectionName") or "") == str(promotion.get("CollectionName") or ""))
        )
        if (
            order_date < pd.Timestamp(promotion["EffectiveStartDate"])
            or order_date > pd.Timestamp(promotion["EffectiveEndDate"])
            or not scope_valid
        ):
            exceptions.append({
                "type": "promotion_scope_or_date_mismatch",
                "sales_order_line_id": int(line.SalesOrderLineID),
                "message": f"Sales order line {int(line.SalesOrderLineID)} uses promotion {int(line.PromotionID)} outside its valid scope or effective dates.",
            })

    price_floor_lookup = price_list_lines.set_index("PriceListLineID")["MinimumUnitPrice"].astype(float).to_dict() if not price_list_lines.empty else {}
    for line in sales_order_lines[sales_order_lines["PriceListLineID"].notna()].itertuples(index=False):
        minimum_unit_price = float(price_floor_lookup.get(int(line.PriceListLineID), float(line.UnitPrice)))
        if round(float(line.UnitPrice), 2) < round(minimum_unit_price, 2) and pd.isna(line.PriceOverrideApprovalID):
            exceptions.append({
                "type": "line_below_price_floor_without_approval",
                "sales_order_line_id": int(line.SalesOrderLineID),
                "message": f"Sales order line {int(line.SalesOrderLineID)} is below the price floor without an override approval.",
            })

    sales_line_lookup = sales_order_lines.set_index("SalesOrderLineID").to_dict("index") if not sales_order_lines.empty else {}
    for line in sales_invoice_lines.itertuples(index=False):
        sales_line = sales_line_lookup.get(int(line.SalesOrderLineID))
        if sales_line is None:
            continue
        comparable_fields = ["BaseListPrice", "UnitPrice", "Discount", "PriceListLineID", "PromotionID", "PriceOverrideApprovalID", "PricingMethod"]
        if any(
            not values_match(
                getattr(line, field_name),
                sales_line.get(field_name),
                numeric=field_name in {"BaseListPrice", "UnitPrice", "Discount"},
            )
            for field_name in comparable_fields
        ):
            exceptions.append({
                "type": "invoice_pricing_lineage_mismatch",
                "sales_invoice_line_id": int(line.SalesInvoiceLineID),
                "message": f"Sales invoice line {int(line.SalesInvoiceLineID)} does not reconcile to its source order-line pricing lineage.",
            })
            if len(exceptions) >= 250:
                break

    if not credit_memo_lines.empty and not context.tables["SalesReturnLine"].empty:
        return_line_lookup = context.tables["SalesReturnLine"].set_index("SalesReturnLineID").to_dict("index")
        for credit_memo_line in credit_memo_lines.itertuples(index=False):
            return_line = return_line_lookup.get(int(credit_memo_line.SalesReturnLineID))
            if return_line is None:
                continue
            matches = sales_invoice_lines[sales_invoice_lines["ShipmentLineID"].astype(int).eq(int(return_line["ShipmentLineID"]))]
            if matches.empty:
                continue
            original_line = matches.iloc[0]
            comparable_fields = ["BaseListPrice", "UnitPrice", "Discount", "PriceListLineID", "PromotionID", "PriceOverrideApprovalID", "PricingMethod"]
            if any(
                not values_match(
                    getattr(credit_memo_line, field_name),
                    original_line[field_name],
                    numeric=field_name in {"BaseListPrice", "UnitPrice", "Discount"},
                )
                for field_name in comparable_fields
            ):
                exceptions.append({
                    "type": "credit_memo_pricing_lineage_mismatch",
                    "credit_memo_line_id": int(credit_memo_line.CreditMemoLineID),
                    "message": f"Credit memo line {int(credit_memo_line.CreditMemoLineID)} does not reconcile to the original billed pricing lineage.",
                })
                if len(exceptions) >= 250:
                    break

    service_order_lines = sales_order_lines.merge(
        items[["ItemID", "ItemGroup"]],
        on="ItemID",
        how="left",
    )
    invalid_service_pricing = service_order_lines[
        service_order_lines["ItemGroup"].eq("Services")
        & (
            service_order_lines["PromotionID"].notna()
            | ~service_order_lines["PricingMethod"].eq("Base List")
        )
    ]
    for row in invalid_service_pricing.head(10).itertuples(index=False):
        exceptions.append({
            "type": "service_pricing_method_conflict",
            "sales_order_line_id": int(row.SalesOrderLineID),
            "message": f"Service line {int(row.SalesOrderLineID)} should remain base-list priced without promotions.",
        })

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_master_data_controls(context: GenerationContext) -> dict[str, Any]:
    employees = context.tables["Employee"].copy()
    items = context.tables["Item"].copy()
    exceptions: list[dict[str, Any]] = []

    if not employees.empty:
        unique_roles = [
            "Chief Executive Officer",
            "Chief Financial Officer",
            "Controller",
            "Production Manager",
            "Accounting Manager",
        ]
        for job_title in unique_roles:
            role_count = int(employees["JobTitle"].eq(job_title).sum())
            if role_count != 1:
                exceptions.append({
                    "type": "unique_role_count_mismatch",
                    "job_title": job_title,
                    "message": f"Expected exactly one {job_title}, found {role_count}.",
                })

        hires = pd.to_datetime(employees["HireDate"], errors="coerce")
        terminations = pd.to_datetime(employees["TerminationDate"], errors="coerce")
        terminated_mask = employees["EmploymentStatus"].eq("Terminated")
        active_mask = employees["EmploymentStatus"].eq("Active")
        leave_mask = employees["EmploymentStatus"].eq("Leave")

        invalid_status_rows = employees[
            (terminated_mask & (terminations.isna() | employees["IsActive"].astype(int).ne(0)))
            | ((active_mask | leave_mask) & (terminations.notna() | employees["IsActive"].astype(int).ne(1)))
            | (terminations.notna() & hires.notna() & terminations.lt(hires))
        ]
        for row in invalid_status_rows.head(10).itertuples(index=False):
            exceptions.append({
                "type": "employee_status_alignment",
                "employee_id": int(row.EmployeeID),
                "message": f"Employee {int(row.EmployeeID)} has inconsistent employment status, termination date, or IsActive flag.",
            })

        terminated_share = round(float(terminated_mask.sum()) / max(len(employees), 1), 4)
        terminated_share_lower_bound = 0.08
        if len(employees) < 30:
            terminated_share_lower_bound = round(1.0 / max(len(employees), 1), 4)
        if terminated_share < terminated_share_lower_bound or terminated_share > 0.15:
            exceptions.append({
                "type": "terminated_share_out_of_band",
                "share": terminated_share,
                "message": (
                    f"Terminated employee share {terminated_share:.4f} is outside the "
                    f"{terminated_share_lower_bound:.4f} to 0.1500 target band."
                ),
            })

        active_employee_ids = set(employees.loc[employees["IsActive"].astype(int).eq(1), "EmployeeID"].astype(int).tolist())
        current_ref_specs = [
            ("CostCenter", "ManagerID"),
            ("Warehouse", "ManagerID"),
            ("WorkCenter", "ManagerEmployeeID"),
            ("Customer", "SalesRepEmployeeID"),
        ]
        for table_name, employee_column in current_ref_specs:
            table = context.tables[table_name]
            if table.empty or employee_column not in table.columns:
                continue
            invalid_refs = table[
                table[employee_column].notna()
                & ~table[employee_column].astype(int).isin(active_employee_ids)
            ]
            for row in invalid_refs.head(10).itertuples(index=False):
                exceptions.append({
                    "type": "inactive_current_master_reference",
                    "table_name": table_name,
                    "employee_column": employee_column,
                    "message": f"{table_name}.{employee_column} points to an employee who is not active at end of range.",
                })

        employee_lookup = employees.set_index("EmployeeID")[["HireDate", "TerminationDate"]].to_dict("index")
        employee_date_specs = [
            ("SalesOrder", "OrderDate", ["SalesRepEmployeeID"]),
            ("CashReceipt", "ReceiptDate", ["RecordedByEmployeeID"]),
            ("CashReceiptApplication", "ApplicationDate", ["AppliedByEmployeeID"]),
            ("SalesReturn", "ReturnDate", ["ReceivedByEmployeeID"]),
            ("CreditMemo", "ApprovedDate", ["ApprovedByEmployeeID"]),
            ("CustomerRefund", "RefundDate", ["ApprovedByEmployeeID"]),
            ("PurchaseRequisition", "RequestDate", ["RequestedByEmployeeID"]),
            ("PurchaseRequisition", "ApprovedDate", ["ApprovedByEmployeeID"]),
            ("PurchaseOrder", "OrderDate", ["CreatedByEmployeeID", "ApprovedByEmployeeID"]),
            ("GoodsReceipt", "ReceiptDate", ["ReceivedByEmployeeID"]),
            ("PurchaseInvoice", "ApprovedDate", ["ApprovedByEmployeeID"]),
            ("DisbursementPayment", "PaymentDate", ["ApprovedByEmployeeID"]),
            ("WorkOrder", "ReleasedDate", ["ReleasedByEmployeeID"]),
            ("WorkOrder", "ClosedDate", ["ClosedByEmployeeID"]),
            ("MaterialIssue", "IssueDate", ["IssuedByEmployeeID"]),
            ("ProductionCompletion", "CompletionDate", ["ReceivedByEmployeeID"]),
            ("WorkOrderClose", "CloseDate", ["ClosedByEmployeeID"]),
            ("TimeClockEntry", "WorkDate", ["EmployeeID", "ApprovedByEmployeeID"]),
            ("LaborTimeEntry", "WorkDate", ["EmployeeID", "ApprovedByEmployeeID"]),
            ("PayrollRegister", "ApprovedDate", ["EmployeeID", "ApprovedByEmployeeID"]),
            ("PayrollPayment", "PaymentDate", ["RecordedByEmployeeID"]),
            ("PayrollLiabilityRemittance", "RemittanceDate", ["ApprovedByEmployeeID"]),
            ("JournalEntry", "CreatedDate", ["CreatedByEmployeeID"]),
            ("JournalEntry", "ApprovedDate", ["ApprovedByEmployeeID"]),
            ("Budget", "ApprovedDate", ["ApprovedByEmployeeID"]),
        ]
        for table_name, date_column, employee_columns in employee_date_specs:
            table = context.tables[table_name]
            if table.empty or date_column not in table.columns:
                continue
            event_dates = pd.to_datetime(table[date_column], errors="coerce")
            for employee_column in employee_columns:
                if employee_column not in table.columns:
                    continue
                active_rows = table[table[employee_column].notna()].copy()
                if active_rows.empty:
                    continue
                for row_index, row in active_rows.head(len(active_rows)).iterrows():
                    employee = employee_lookup.get(int(row[employee_column]))
                    event_date = event_dates.loc[row_index]
                    if employee is None or pd.isna(event_date):
                        continue
                    hire_date = pd.Timestamp(employee["HireDate"])
                    termination_date = pd.Timestamp(employee["TerminationDate"]) if pd.notna(employee["TerminationDate"]) else None
                    if event_date < hire_date or (termination_date is not None and event_date > termination_date):
                        exceptions.append({
                            "type": "employee_activity_outside_employment_dates",
                            "table_name": table_name,
                            "employee_column": employee_column,
                            "employee_id": int(row[employee_column]),
                            "message": f"{table_name}.{employee_column} references employee {int(row[employee_column])} outside the employee's valid employment dates.",
                        })
                        if len(exceptions) >= 250:
                            break
                if len(exceptions) >= 250:
                    break
            if len(exceptions) >= 250:
                break

    if not items.empty:
        sellable = items[items["RevenueAccountID"].notna()].copy()
        generic_names = sellable["ItemName"].astype(str).str.fullmatch(r"(Furniture|Lighting|Textiles|Accessories) Item \d{4}")
        if generic_names.any():
            for row in sellable[generic_names].head(10).itertuples(index=False):
                exceptions.append({
                    "type": "generic_item_name",
                    "item_id": int(row.ItemID),
                    "message": f"Sellable item {int(row.ItemID)} still uses the old generic naming pattern.",
                })

        required_columns_by_group = {
            "Furniture": ["CollectionName", "StyleFamily", "PrimaryMaterial", "Finish", "SizeDescriptor", "LifecycleStatus", "LaunchDate"],
            "Lighting": ["CollectionName", "StyleFamily", "PrimaryMaterial", "Finish", "LifecycleStatus", "LaunchDate"],
            "Textiles": ["CollectionName", "StyleFamily", "PrimaryMaterial", "Color", "SizeDescriptor", "LifecycleStatus", "LaunchDate"],
            "Accessories": ["StyleFamily", "PrimaryMaterial", "Finish", "LifecycleStatus", "LaunchDate"],
            "Raw Materials": ["PrimaryMaterial", "SizeDescriptor", "LifecycleStatus", "LaunchDate"],
            "Packaging": ["PrimaryMaterial", "SizeDescriptor", "LifecycleStatus", "LaunchDate"],
            "Services": ["LifecycleStatus", "LaunchDate"],
        }
        for item_group, required_columns in required_columns_by_group.items():
            rows = items[items["ItemGroup"].eq(item_group)]
            for column_name in required_columns:
                invalid_rows = rows[rows[column_name].isna() | rows[column_name].astype(str).eq("")]
                for row in invalid_rows.head(5).itertuples(index=False):
                    exceptions.append({
                        "type": "missing_item_catalog_attribute",
                        "item_id": int(row.ItemID),
                        "column_name": column_name,
                        "message": f"Item {int(row.ItemID)} is missing required catalog attribute {column_name}.",
                    })

        lifecycle = items["LifecycleStatus"].astype(str)
        launch_dates = pd.to_datetime(items["LaunchDate"], errors="coerce")
        invalid_lifecycle_rows = items[
            launch_dates.isna()
            | ((lifecycle == "Discontinued") & items["IsActive"].astype(int).ne(0))
            | ((lifecycle.isin(["Core", "Seasonal"])) & items["IsActive"].astype(int).ne(1))
        ]
        for row in invalid_lifecycle_rows.head(10).itertuples(index=False):
            exceptions.append({
                "type": "item_lifecycle_alignment",
                "item_id": int(row.ItemID),
                "message": f"Item {int(row.ItemID)} has inconsistent lifecycle, launch date, or IsActive state.",
            })

        item_launch_lookup = items.set_index("ItemID")["LaunchDate"].to_dict()
        item_current_active_lookup = items.set_index("ItemID")["IsActive"].astype(int).to_dict()
        item_lifecycle_lookup = items.set_index("ItemID")["LifecycleStatus"].astype(str).to_dict()
        internal_prelaunch_tables = {
            "PurchaseRequisition",
            "PurchaseOrderLine",
            "GoodsReceiptLine",
            "PurchaseInvoiceLine",
            "WorkOrder",
            "ProductionCompletionLine",
        }
        item_date_specs = [
            ("SalesOrderLine", "ItemID", context.tables["SalesOrder"][["SalesOrderID", "OrderDate"]], "SalesOrderID", "OrderDate"),
            ("PurchaseRequisition", "ItemID", None, None, "RequestDate"),
            ("PurchaseOrderLine", "ItemID", context.tables["PurchaseOrder"][["PurchaseOrderID", "OrderDate"]], "PurchaseOrderID", "OrderDate"),
            ("GoodsReceiptLine", "ItemID", context.tables["GoodsReceipt"][["GoodsReceiptID", "ReceiptDate"]], "GoodsReceiptID", "ReceiptDate"),
            ("PurchaseInvoiceLine", "ItemID", context.tables["PurchaseInvoice"][["PurchaseInvoiceID", "InvoiceDate"]], "PurchaseInvoiceID", "InvoiceDate"),
            ("WorkOrder", "ItemID", None, None, "ReleasedDate"),
            ("ShipmentLine", "ItemID", context.tables["Shipment"][["ShipmentID", "ShipmentDate"]], "ShipmentID", "ShipmentDate"),
            ("SalesInvoiceLine", "ItemID", context.tables["SalesInvoice"][["SalesInvoiceID", "InvoiceDate"]], "SalesInvoiceID", "InvoiceDate"),
            ("SalesReturnLine", "ItemID", context.tables["SalesReturn"][["SalesReturnID", "ReturnDate"]], "SalesReturnID", "ReturnDate"),
            ("ProductionCompletionLine", "ItemID", context.tables["ProductionCompletion"][["ProductionCompletionID", "CompletionDate"]], "ProductionCompletionID", "CompletionDate"),
        ]
        for table_name, item_column, header_df, link_column, date_column in item_date_specs:
            table = context.tables[table_name]
            if table.empty or item_column not in table.columns:
                continue
            dated_rows = table.copy()
            if header_df is not None and link_column is not None:
                dated_rows = dated_rows.merge(header_df, on=link_column, how="left")
            event_dates = pd.to_datetime(dated_rows[date_column], errors="coerce")
            for row_index, row in dated_rows[dated_rows[item_column].notna()].iterrows():
                item_id = int(row[item_column])
                launch_date = item_launch_lookup.get(item_id)
                if launch_date is None or pd.isna(event_dates.loc[row_index]):
                    continue
                is_internal_prelaunch = table_name in internal_prelaunch_tables
                if pd.Timestamp(event_dates.loc[row_index]) < pd.Timestamp(launch_date) and not is_internal_prelaunch:
                    exceptions.append({
                        "type": "item_used_before_launch",
                        "table_name": table_name,
                        "item_id": item_id,
                        "message": f"{table_name} references item {item_id} before its launch date.",
                    })
                if int(item_current_active_lookup.get(item_id, 1)) != 1 and str(item_lifecycle_lookup.get(item_id, "")) == "Discontinued":
                    exceptions.append({
                        "type": "inactive_item_in_activity",
                        "table_name": table_name,
                        "item_id": item_id,
                        "message": f"{table_name} references discontinued item {item_id}.",
                    })
                if len(exceptions) >= 250:
                    break
            if len(exceptions) >= 250:
                break

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


def validate_phase13(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase6(context)
    exceptions = list(results["exceptions"])

    o2c_controls = validate_o2c_phase11_controls(context)
    if o2c_controls["exception_count"]:
        exceptions.append(f"O2C control exceptions: {o2c_controls['exception_count']}.")

    p2p_controls = validate_p2p_phase9_controls(context)
    if p2p_controls["exception_count"]:
        exceptions.append(f"P2P control exceptions: {p2p_controls['exception_count']}.")

    journal_controls = validate_journal_controls(context)
    if journal_controls["exception_count"]:
        exceptions.append(f"Journal control exceptions: {journal_controls['exception_count']}.")

    manufacturing_controls = validate_manufacturing_controls(context)
    if manufacturing_controls["exception_count"]:
        exceptions.append(f"Manufacturing control exceptions: {manufacturing_controls['exception_count']}.")

    payroll_controls = validate_payroll_controls(context)
    if payroll_controls["exception_count"]:
        exceptions.append(f"Payroll control exceptions: {payroll_controls['exception_count']}.")

    phase13_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": o2c_controls,
        "p2p_controls": p2p_controls,
        "journal_controls": journal_controls,
        "manufacturing_controls": manufacturing_controls,
        "payroll_controls": payroll_controls,
    }
    if store:
        context.validation_results["phase13"] = phase13_results
        context.validation_results["phase12"] = phase13_results
        context.validation_results["phase11"] = phase13_results
        context.validation_results["phase9"] = phase13_results
    return phase13_results


def validate_phase14(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase13(context, store=False)
    exceptions = list(results["exceptions"])

    routing_controls = validate_routing_controls(context)
    if routing_controls["exception_count"]:
        exceptions.append(f"Routing control exceptions: {routing_controls['exception_count']}.")

    phase14_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": routing_controls,
    }
    if store:
        context.validation_results["phase14"] = phase14_results
        context.validation_results["phase13"] = phase14_results
        context.validation_results["phase12"] = phase14_results
        context.validation_results["phase11"] = phase14_results
        context.validation_results["phase9"] = phase14_results
    return phase14_results


def validate_phase15(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    return validate_phase15_2(context, scope="full", store=store)


def validate_phase15_2(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    normalized_scope = str(scope).strip().lower()
    if normalized_scope not in {"core", "operational", "full"}:
        raise ValueError(f"Unsupported validation scope: {scope}")

    results = validate_phase6(context)
    exceptions = list(results["exceptions"])

    empty_control = {"exception_count": 0, "exceptions": []}
    o2c_controls: dict[str, Any] = empty_control
    p2p_controls: dict[str, Any] = empty_control
    journal_controls: dict[str, Any] = empty_control
    manufacturing_controls: dict[str, Any] = empty_control
    payroll_controls: dict[str, Any] = empty_control
    routing_controls: dict[str, Any] = empty_control
    capacity_controls: dict[str, Any] = empty_control

    if normalized_scope in {"operational", "full"}:
        o2c_controls = validate_o2c_phase11_controls(context)
        if o2c_controls["exception_count"]:
            exceptions.append(f"O2C control exceptions: {o2c_controls['exception_count']}.")

        p2p_controls = validate_p2p_phase9_controls(context)
        if p2p_controls["exception_count"]:
            exceptions.append(f"P2P control exceptions: {p2p_controls['exception_count']}.")

        journal_controls = validate_journal_controls(context)
        if journal_controls["exception_count"]:
            exceptions.append(f"Journal control exceptions: {journal_controls['exception_count']}.")

        manufacturing_controls = validate_manufacturing_controls(context)
        if manufacturing_controls["exception_count"]:
            exceptions.append(f"Manufacturing control exceptions: {manufacturing_controls['exception_count']}.")

        payroll_controls = validate_payroll_controls(context)
        if payroll_controls["exception_count"]:
            exceptions.append(f"Payroll control exceptions: {payroll_controls['exception_count']}.")

        routing_controls = validate_routing_controls(context)
        if routing_controls["exception_count"]:
            exceptions.append(f"Routing control exceptions: {routing_controls['exception_count']}.")

        capacity_controls = validate_capacity_controls(context)
        if capacity_controls["exception_count"]:
            exceptions.append(f"Capacity control exceptions: {capacity_controls['exception_count']}.")

    phase15_2_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": o2c_controls,
        "p2p_controls": p2p_controls,
        "journal_controls": journal_controls,
        "manufacturing_controls": manufacturing_controls,
        "payroll_controls": payroll_controls,
        "routing_controls": routing_controls,
        "capacity_controls": capacity_controls,
    }
    if store:
        context.validation_results["phase15_2"] = phase15_2_results
        context.validation_results["phase15"] = phase15_2_results
        context.validation_results["phase14"] = phase15_2_results
        context.validation_results["phase13"] = phase15_2_results
        context.validation_results["phase12"] = phase15_2_results
        context.validation_results["phase11"] = phase15_2_results
        context.validation_results["phase9"] = phase15_2_results
    return phase15_2_results


def validate_phase16(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase15_2(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    normalized_scope = str(scope).strip().lower()
    time_clock_controls: dict[str, Any] = {"exception_count": 0, "exceptions": []}
    if normalized_scope in {"operational", "full"}:
        time_clock_controls = validate_time_clock_controls(context)
        if time_clock_controls["exception_count"]:
            exceptions.append(f"Time-clock control exceptions: {time_clock_controls['exception_count']}.")

    phase16_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": time_clock_controls,
    }
    if store:
        context.validation_results["phase16"] = phase16_results
        context.validation_results["phase15_2"] = phase16_results
        context.validation_results["phase15"] = phase16_results
        context.validation_results["phase14"] = phase16_results
        context.validation_results["phase13"] = phase16_results
        context.validation_results["phase12"] = phase16_results
        context.validation_results["phase11"] = phase16_results
        context.validation_results["phase9"] = phase16_results
    return phase16_results


def validate_phase17(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase16(context, scope=scope, store=False)

    phase17_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": list(results["exceptions"]),
        "validation_scope": results["validation_scope"],
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
    }
    if store:
        context.validation_results["phase17"] = phase17_results
        context.validation_results["phase16"] = phase17_results
        context.validation_results["phase15_2"] = phase17_results
        context.validation_results["phase15"] = phase17_results
        context.validation_results["phase14"] = phase17_results
        context.validation_results["phase13"] = phase17_results
        context.validation_results["phase12"] = phase17_results
        context.validation_results["phase11"] = phase17_results
        context.validation_results["phase9"] = phase17_results
    return phase17_results


def validate_phase18(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase17(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    normalized_scope = str(scope).strip().lower()
    master_data_controls: dict[str, Any] = {"exception_count": 0, "exceptions": []}
    if normalized_scope in {"operational", "full"}:
        master_data_controls = validate_master_data_controls(context)
        if master_data_controls["exception_count"]:
            exceptions.append(f"Master data control exceptions: {master_data_controls['exception_count']}.")

    phase18_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": master_data_controls,
    }
    if store:
        context.validation_results["phase18"] = phase18_results
        context.validation_results["phase17"] = phase18_results
        context.validation_results["phase16"] = phase18_results
        context.validation_results["phase15_2"] = phase18_results
        context.validation_results["phase15"] = phase18_results
        context.validation_results["phase14"] = phase18_results
        context.validation_results["phase13"] = phase18_results
        context.validation_results["phase12"] = phase18_results
        context.validation_results["phase11"] = phase18_results
        context.validation_results["phase9"] = phase18_results
    return phase18_results


def validate_phase19(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase18(context, scope=scope, store=False)

    phase19_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": list(results["exceptions"]),
        "validation_scope": results["validation_scope"],
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": results["master_data_controls"],
    }
    if store:
        context.validation_results["phase19"] = phase19_results
        context.validation_results["phase18"] = phase19_results
        context.validation_results["phase17"] = phase19_results
        context.validation_results["phase16"] = phase19_results
        context.validation_results["phase15_2"] = phase19_results
        context.validation_results["phase15"] = phase19_results
        context.validation_results["phase14"] = phase19_results
        context.validation_results["phase13"] = phase19_results
        context.validation_results["phase12"] = phase19_results
        context.validation_results["phase11"] = phase19_results
        context.validation_results["phase9"] = phase19_results
    return phase19_results


def validate_phase20(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase19(context, scope=scope, store=False)

    phase20_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": list(results["exceptions"]),
        "validation_scope": results["validation_scope"],
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": results["master_data_controls"],
    }
    if store:
        context.validation_results["phase20"] = phase20_results
        context.validation_results["phase19"] = phase20_results
        context.validation_results["phase18"] = phase20_results
        context.validation_results["phase17"] = phase20_results
        context.validation_results["phase16"] = phase20_results
        context.validation_results["phase15_2"] = phase20_results
        context.validation_results["phase15"] = phase20_results
        context.validation_results["phase14"] = phase20_results
        context.validation_results["phase13"] = phase20_results
        context.validation_results["phase12"] = phase20_results
        context.validation_results["phase11"] = phase20_results
        context.validation_results["phase9"] = phase20_results
    return phase20_results


def validate_phase21(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase20(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    normalized_scope = str(scope).strip().lower()
    workforce_planning_controls: dict[str, Any] = {"exception_count": 0, "exceptions": []}
    if normalized_scope in {"operational", "full"}:
        workforce_planning_controls = validate_workforce_planning_controls(context)
        if workforce_planning_controls["exception_count"]:
            exceptions.append(
                f"Workforce planning control exceptions: {workforce_planning_controls['exception_count']}."
            )

    phase21_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": results["master_data_controls"],
        "workforce_planning_controls": workforce_planning_controls,
    }
    if store:
        context.validation_results["phase21"] = phase21_results
        context.validation_results["phase20"] = phase21_results
        context.validation_results["phase19"] = phase21_results
        context.validation_results["phase18"] = phase21_results
        context.validation_results["phase17"] = phase21_results
        context.validation_results["phase16"] = phase21_results
        context.validation_results["phase15_2"] = phase21_results
        context.validation_results["phase15"] = phase21_results
        context.validation_results["phase14"] = phase21_results
        context.validation_results["phase13"] = phase21_results
        context.validation_results["phase12"] = phase21_results
        context.validation_results["phase11"] = phase21_results
        context.validation_results["phase9"] = phase21_results
    return phase21_results


def validate_phase22(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase21(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    normalized_scope = str(scope).strip().lower()
    planning_controls: dict[str, Any] = {"exception_count": 0, "exceptions": []}
    if normalized_scope in {"operational", "full"}:
        planning_controls = validate_planning_controls(context)
        if planning_controls["exception_count"]:
            exceptions.append(
                f"Planning control exceptions: {planning_controls['exception_count']}."
            )

    phase22_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": results["master_data_controls"],
        "workforce_planning_controls": results["workforce_planning_controls"],
        "planning_controls": planning_controls,
    }
    if store:
        context.validation_results["phase22"] = phase22_results
        context.validation_results["phase21"] = phase22_results
        context.validation_results["phase20"] = phase22_results
        context.validation_results["phase19"] = phase22_results
        context.validation_results["phase18"] = phase22_results
        context.validation_results["phase17"] = phase22_results
        context.validation_results["phase16"] = phase22_results
        context.validation_results["phase15_2"] = phase22_results
        context.validation_results["phase15"] = phase22_results
        context.validation_results["phase14"] = phase22_results
        context.validation_results["phase13"] = phase22_results
        context.validation_results["phase12"] = phase22_results
        context.validation_results["phase11"] = phase22_results
        context.validation_results["phase9"] = phase22_results
    return phase22_results


def validate_phase23(
    context: GenerationContext,
    scope: str = "full",
    store: bool = True,
) -> dict[str, Any]:
    results = validate_phase22(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    normalized_scope = str(scope).strip().lower()
    pricing_controls: dict[str, Any] = {"exception_count": 0, "exceptions": []}
    if normalized_scope in {"operational", "full"}:
        pricing_controls = validate_pricing_controls(context)
        if pricing_controls["exception_count"]:
            exceptions.append(
                f"Pricing control exceptions: {pricing_controls['exception_count']}."
            )

    phase23_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "validation_scope": normalized_scope,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results["time_clock_controls"],
        "master_data_controls": results["master_data_controls"],
        "workforce_planning_controls": results["workforce_planning_controls"],
        "planning_controls": results["planning_controls"],
        "pricing_controls": pricing_controls,
    }
    if store:
        context.validation_results["phase23"] = phase23_results
        context.validation_results["phase22"] = phase23_results
        context.validation_results["phase21"] = phase23_results
        context.validation_results["phase20"] = phase23_results
        context.validation_results["phase19"] = phase23_results
        context.validation_results["phase18"] = phase23_results
        context.validation_results["phase17"] = phase23_results
        context.validation_results["phase16"] = phase23_results
        context.validation_results["phase15_2"] = phase23_results
        context.validation_results["phase15"] = phase23_results
        context.validation_results["phase14"] = phase23_results
        context.validation_results["phase13"] = phase23_results
        context.validation_results["phase12"] = phase23_results
        context.validation_results["phase11"] = phase23_results
        context.validation_results["phase9"] = phase23_results
    return phase23_results


def validate_phase12(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase15(context, store=False)
    if store:
        context.validation_results["phase12"] = results
    return results


def validate_phase11(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase15(context, store=False)
    if store:
        context.validation_results["phase11"] = results
    return results


def validate_phase9(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase15(context, store=False)
    if store:
        context.validation_results["phase9"] = results
    return results


def validate_phase8(context: GenerationContext, scope: str = "full") -> dict[str, Any]:
    results = validate_phase23(context, scope=scope, store=False)
    exceptions = list(results["exceptions"])

    if context.settings.anomaly_mode != "none" and not context.anomaly_log:
        exceptions.append("Anomaly mode is enabled but no anomalies were logged.")

    phase8_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "anomaly_count": len(context.anomaly_log),
        "o2c_controls": results["o2c_controls"],
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
        "manufacturing_controls": results["manufacturing_controls"],
        "payroll_controls": results["payroll_controls"],
        "routing_controls": results["routing_controls"],
        "capacity_controls": results["capacity_controls"],
        "time_clock_controls": results.get("time_clock_controls", {"exception_count": 0, "exceptions": []}),
        "master_data_controls": results.get("master_data_controls", {"exception_count": 0, "exceptions": []}),
        "workforce_planning_controls": results.get("workforce_planning_controls", {"exception_count": 0, "exceptions": []}),
        "planning_controls": results.get("planning_controls", {"exception_count": 0, "exceptions": []}),
        "pricing_controls": results.get("pricing_controls", {"exception_count": 0, "exceptions": []}),
    }
    context.validation_results["phase8"] = phase8_results
    return phase8_results
