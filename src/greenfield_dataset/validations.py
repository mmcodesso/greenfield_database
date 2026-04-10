from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from greenfield_dataset.journals import ACCRUAL_ACCOUNT_METADATA, accrual_journal_details
from greenfield_dataset.master_data import ACCRUAL_SERVICE_ITEMS
from greenfield_dataset.manufacturing import (
    manufacturing_open_state,
    open_work_order_remaining_quantity_map,
    work_order_actual_conversion_cost_map,
    work_order_completed_quantity_map,
    work_order_material_issue_cost_map,
    work_order_standard_direct_labor_cost_map,
    work_order_standard_overhead_cost_map,
    work_order_standard_conversion_cost_map,
    work_order_standard_material_cost_map,
)
from greenfield_dataset.o2c import (
    credit_memo_allocation_map,
    credit_memo_refunded_amounts,
    invoice_cash_application_amounts,
    invoice_credit_memo_amounts,
    invoice_settled_amounts,
    opening_inventory_map,
    o2c_open_state,
    receipt_applied_amounts,
    sales_order_line_shipped_quantities,
    shipment_line_billed_quantities,
    shipment_line_returned_quantities,
)
from greenfield_dataset.p2p import (
    goods_receipt_line_invoiced_quantities,
    invoice_paid_amounts,
    po_line_received_quantities,
    purchase_invoice_line_matched_basis_map,
)
from greenfield_dataset.payroll import (
    monthly_direct_labor_reclass_amount,
    monthly_factory_overhead_amount,
    monthly_manufacturing_overhead_pool_amount,
    payroll_liability_recorded_amounts,
    payroll_liability_remitted_amounts,
)
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, qty


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
            if round(float(credit_memo_line.UnitPrice), 2) != round(float(original_line["UnitPrice"]), 2) or money(float(credit_memo_line.LineTotal)) != expected_line_total:
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

    return {
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "open_state": o2c_open_state(context),
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

    if context.settings.anomaly_mode != "none" and not context.anomaly_log:
        exceptions.append("Anomaly mode is enabled but no anomalies were logged.")

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


def validate_payroll_controls(context: GenerationContext) -> dict[str, Any]:
    periods = context.tables["PayrollPeriod"]
    labor_entries = context.tables["LaborTimeEntry"]
    registers = context.tables["PayrollRegister"]
    register_lines = context.tables["PayrollRegisterLine"]
    payments = context.tables["PayrollPayment"]
    remittances = context.tables["PayrollLiabilityRemittance"]
    employees = context.tables["Employee"]
    work_orders = context.tables["WorkOrder"]
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
            for period in processed_periods.itertuples(index=False):
                active_count_by_period[int(period.PayrollPeriodID)] = int(
                    (
                        employees["IsActive"].eq(1)
                        & employee_hires.le(pd.Timestamp(period.PeriodEndDate))
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
        invalid_direct_labor = []
        for entry in labor_entries.itertuples(index=False):
            if str(entry.LaborType) != "Direct Manufacturing" or pd.isna(entry.WorkOrderID):
                continue
            item_id = work_order_item_ids.get(int(entry.WorkOrderID))
            if item_id is None or str(supply_modes.get(int(item_id))) != "Manufactured":
                invalid_direct_labor.append(int(entry.LaborTimeEntryID))
        if invalid_direct_labor:
            exceptions.append({
                "type": "direct_labor_invalid_work_order",
                "message": f"Direct labor entries reference invalid or non-manufactured work orders: {invalid_direct_labor[:5]}.",
            })

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


def validate_phase12(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase13(context, store=False)
    if store:
        context.validation_results["phase12"] = results
    return results


def validate_phase11(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase13(context, store=False)
    if store:
        context.validation_results["phase11"] = results
    return results


def validate_phase9(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase13(context, store=False)
    if store:
        context.validation_results["phase9"] = results
    return results


def validate_phase8(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase13(context, store=False)
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
    }
    context.validation_results["phase8"] = phase8_results
    return phase8_results
