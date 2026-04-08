from __future__ import annotations

from typing import Any

import pandas as pd

from greenfield_dataset.p2p import (
    goods_receipt_line_invoiced_quantities,
    invoice_paid_amounts,
    po_line_received_quantities,
    purchase_invoice_line_matched_basis_map,
)
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext


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
        "Item": context.settings.item_count,
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
    if not cash_receipts.empty:
        valid_invoice_ids = set(sales_invoices["SalesInvoiceID"].astype(int))
        receipt_invoice_ids = set(cash_receipts["SalesInvoiceID"].dropna().astype(int))
        orphan_ids = sorted(receipt_invoice_ids - valid_invoice_ids)
        if orphan_ids:
            exceptions.append(f"Cash receipts reference missing sales invoices: {orphan_ids[:5]}.")

        receipt_totals = cash_receipts.groupby("SalesInvoiceID")["Amount"].sum().round(2)
        invoice_totals = sales_invoices.set_index("SalesInvoiceID")["GrandTotal"].astype(float).round(2)
        overpaid = [
            int(invoice_id)
            for invoice_id, amount in receipt_totals.items()
            if round(float(amount), 2) > round(float(invoice_totals.get(invoice_id, 0.0)), 2)
        ]
        if overpaid:
            exceptions.append(f"Cash receipts exceed sales invoice totals: {overpaid[:5]}.")

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

    def gl_credit_net(account_number: str) -> float:
        account_id = account_id_by_number(context, account_number)
        account_rows = operational_gl[operational_gl["AccountID"].astype(int).eq(account_id)]
        return round(float(account_rows["Credit"].sum()) - float(account_rows["Debit"].sum()), 2)

    cleared_grni = round(sum(purchase_invoice_line_matched_basis_map(context).values()), 2)
    checks = [
        {
            "name": "AR",
            "expected": round(
                float(context.tables["SalesInvoice"]["GrandTotal"].sum())
                - float(context.tables["CashReceipt"]["Amount"].sum()),
                2,
            ),
            "actual": gl_debit_net("1020"),
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
                - float(context.tables["ShipmentLine"]["ExtendedStandardCost"].sum()),
                2,
            ),
            "actual": gl_debit_net("1040") + gl_debit_net("1045"),
        },
        {
            "name": "COGS",
            "expected": round(float(context.tables["ShipmentLine"]["ExtendedStandardCost"].sum()), 2),
            "actual": round(
                gl_debit_net("5010") + gl_debit_net("5020") + gl_debit_net("5030") + gl_debit_net("5040"),
                2,
            ),
        },
        {
            "name": "GRNI",
            "expected": round(
                float(context.tables["GoodsReceiptLine"]["ExtendedStandardCost"].sum()) - cleared_grni,
                2,
            ),
            "actual": gl_credit_net("2020"),
        },
    ]

    for check in checks:
        if round(float(check["expected"]) - float(check["actual"]), 2) != 0:
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
    purchase_invoices = context.tables["PurchaseInvoice"]
    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    exceptions: list[dict[str, Any]] = []

    requisition_item_ids = requisitions.set_index("RequisitionID")["ItemID"].to_dict() if not requisitions.empty else {}
    valid_requisition_ids = set(requisitions["RequisitionID"].astype(int)) if not requisitions.empty else set()
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
    reversals = journal_entries[journal_entries["EntryType"].eq("Accrual Reversal")]
    for reversal in reversals.itertuples(index=False):
        reverses_id = reversal.ReversesJournalEntryID
        if pd.isna(reverses_id):
            exceptions.append({
                "type": "missing_reversal_link",
                "journal_entry_id": int(reversal.JournalEntryID),
                "message": "Accrual reversal is missing ReversesJournalEntryID.",
            })
            continue

        original = journal_lookup.get(int(reverses_id))
        if original is None or original["EntryType"] != "Accrual":
            exceptions.append({
                "type": "invalid_reversal_link",
                "journal_entry_id": int(reversal.JournalEntryID),
                "message": "Accrual reversal does not reference a valid Accrual journal entry.",
            })
            continue

        original_year = pd.Timestamp(original["PostingDate"]).year
        original_month = pd.Timestamp(original["PostingDate"]).month
        expected_year, expected_month = next_month(int(original_year), int(original_month))
        expected_posting_date = first_business_day(expected_year, expected_month).strftime("%Y-%m-%d")
        if str(reversal.PostingDate) != expected_posting_date:
            exceptions.append({
                "type": "late_reversal",
                "journal_entry_id": int(reversal.JournalEntryID),
                "message": "Accrual reversal was not posted on the first business day of the following month.",
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
        "Payroll Accrual": len(fiscal_months(context)) * len(context.tables["CostCenter"]),
        "Payroll Settlement": max(len(fiscal_months(context)) - 1, 0) * len(context.tables["CostCenter"]),
        "Rent": len(fiscal_months(context)) * 2,
        "Utilities": len(fiscal_months(context)),
        "Depreciation": len(fiscal_months(context)) * 3,
        "Accrual": len(fiscal_months(context)),
        "Accrual Reversal": max(len(fiscal_months(context)) - 1, 0),
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


def validate_phase9(context: GenerationContext, store: bool = True) -> dict[str, Any]:
    results = validate_phase6(context)
    exceptions = list(results["exceptions"])

    p2p_controls = validate_p2p_phase9_controls(context)
    if p2p_controls["exception_count"]:
        exceptions.append(f"P2P phase 9 control exceptions: {p2p_controls['exception_count']}.")

    journal_controls = validate_journal_controls(context)
    if journal_controls["exception_count"]:
        exceptions.append(f"Journal control exceptions: {journal_controls['exception_count']}.")

    phase9_results: dict[str, Any] = {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": results["gl_balance"],
        "trial_balance_difference": results["trial_balance_difference"],
        "account_rollforward": results["account_rollforward"],
        "p2p_controls": p2p_controls,
        "journal_controls": journal_controls,
    }
    if store:
        context.validation_results["phase9"] = phase9_results
    return phase9_results


def validate_phase8(context: GenerationContext) -> dict[str, Any]:
    results = validate_phase9(context, store=False)
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
        "p2p_controls": results["p2p_controls"],
        "journal_controls": results["journal_controls"],
    }
    context.validation_results["phase8"] = phase8_results
    return phase8_results
