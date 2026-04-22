from __future__ import annotations

from typing import Any

import pandas as pd

from generator_dataset.fixed_assets import capex_item_definitions, capex_plan_events, load_capex_plan
from generator_dataset.p2p import (
    append_rows,
    approver_id,
    cost_center_id,
    employee_ids_for_cost_center,
    update_purchase_invoice_statuses,
    update_purchase_order_statuses,
)
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import format_doc_number, money, next_id, qty


def _account_id_by_number(context: GenerationContext, account_number: str) -> int:
    matches = context.tables["Account"].loc[
        context.tables["Account"]["AccountNumber"].astype(str).eq(str(account_number)),
        "AccountID",
    ]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def _item_id_by_code(context: GenerationContext, item_code: str) -> int:
    matches = context.tables["Item"].loc[
        context.tables["Item"]["ItemCode"].astype(str).eq(str(item_code)),
        "ItemID",
    ]
    if matches.empty:
        raise ValueError(f"CAPEX item {item_code} is not loaded.")
    return int(matches.iloc[0])


def _warehouse_id_by_name(context: GenerationContext, warehouse_name: str | None) -> int | None:
    warehouses = context.tables["Warehouse"]
    if warehouses.empty:
        return None
    if warehouse_name:
        matches = warehouses.loc[warehouses["WarehouseName"].astype(str).eq(str(warehouse_name)), "WarehouseID"]
        if not matches.empty:
            return int(matches.iloc[0])
    return int(warehouses.sort_values("WarehouseID").iloc[0]["WarehouseID"])


def _work_center_id_by_code(context: GenerationContext, work_center_code: str | None) -> int | None:
    if not work_center_code or context.tables["WorkCenter"].empty:
        return None
    matches = context.tables["WorkCenter"].loc[
        context.tables["WorkCenter"]["WorkCenterCode"].astype(str).eq(str(work_center_code)),
        "WorkCenterID",
    ]
    if matches.empty:
        return None
    return int(matches.iloc[0])


def _approved_supplier_id(context: GenerationContext, supplier_category: str | None) -> int:
    suppliers = context.tables["Supplier"].copy()
    approved = suppliers[suppliers["IsApproved"].astype(int).eq(1)]
    if approved.empty:
        approved = suppliers
    if supplier_category:
        matches = approved[approved["SupplierCategory"].astype(str).eq(str(supplier_category))]
        if not matches.empty:
            return int(matches.sort_values("SupplierID").iloc[0]["SupplierID"])
    if approved.empty:
        raise ValueError("At least one supplier is required for CAPEX generation.")
    return int(approved.sort_values("SupplierID").iloc[0]["SupplierID"])


def _requestor_id(context: GenerationContext, cost_center_name_value: str, event_date: pd.Timestamp) -> int:
    center_id = cost_center_id(context, cost_center_name_value)
    employee_ids = employee_ids_for_cost_center(context, center_id, event_date)
    if employee_ids:
        return int(employee_ids[0])
    return approver_id(context, event_date=event_date)


def _warehouse_receiver_id(context: GenerationContext, event_date: pd.Timestamp) -> int:
    warehouse_center_id = cost_center_id(context, "Warehouse")
    employee_ids = employee_ids_for_cost_center(context, warehouse_center_id, event_date)
    if employee_ids:
        return int(employee_ids[0])
    return approver_id(context, event_date=event_date)


def _purchasing_creator_id(context: GenerationContext, event_date: pd.Timestamp) -> int:
    purchasing_center_id = cost_center_id(context, "Purchasing")
    employee_ids = employee_ids_for_cost_center(context, purchasing_center_id, event_date)
    if employee_ids:
        return int(employee_ids[0])
    return approver_id(context, event_date=event_date)


def _first_business_day_on_or_after(value: pd.Timestamp | str) -> pd.Timestamp:
    current = pd.Timestamp(value)
    while current.day_name() in {"Saturday", "Sunday"}:
        current = current + pd.Timedelta(days=1)
    return current


def _capex_dates(event_date: pd.Timestamp) -> dict[str, pd.Timestamp]:
    requisition_date = max(
        pd.Timestamp(year=event_date.year, month=event_date.month, day=1),
        event_date - pd.Timedelta(days=10),
    )
    order_date = max(requisition_date, event_date - pd.Timedelta(days=7))
    receipt_date = max(order_date, event_date - pd.Timedelta(days=2))
    invoice_date = event_date
    approved_date = _first_business_day_on_or_after(event_date)
    payment_date = _first_business_day_on_or_after(event_date + pd.Timedelta(days=12))
    return {
        "requisition_date": requisition_date,
        "order_date": order_date,
        "receipt_date": receipt_date,
        "invoice_date": invoice_date,
        "approved_date": approved_date,
        "payment_date": payment_date,
    }


def _asset_id_by_code(context: GenerationContext, asset_code: str) -> int:
    fixed_assets = context.tables["FixedAsset"]
    matches = fixed_assets.loc[fixed_assets["AssetCode"].astype(str).eq(str(asset_code)), "FixedAssetID"]
    if matches.empty:
        raise ValueError(f"CAPEX asset {asset_code} is not loaded.")
    return int(matches.iloc[0])


def _mark_asset_disposed(context: GenerationContext, fixed_asset_id: int, disposal_date: str) -> None:
    mask = context.tables["FixedAsset"]["FixedAssetID"].astype(int).eq(int(fixed_asset_id))
    context.tables["FixedAsset"].loc[mask, "Status"] = "Disposed"
    context.tables["FixedAsset"].loc[mask, "DisposalDate"] = str(disposal_date)


def _scheduled_payment_amount(principal_amount: float, annual_interest_rate: float, term_months: int) -> float:
    if term_months <= 0:
        return 0.0
    monthly_rate = float(annual_interest_rate) / 12.0
    if monthly_rate <= 0:
        return money(float(principal_amount) / float(term_months))
    payment = float(principal_amount) * monthly_rate / (1.0 - (1.0 + monthly_rate) ** (-int(term_months)))
    return money(payment)


def _build_debt_schedule(
    context: GenerationContext,
    debt_agreement_id: int,
    payment_start_date: str,
    principal_amount: float,
    annual_interest_rate: float,
    term_months: int,
) -> list[dict[str, Any]]:
    schedule_rows: list[dict[str, Any]] = []
    balance = money(principal_amount)
    scheduled_payment = _scheduled_payment_amount(balance, annual_interest_rate, term_months)
    payment_anchor = pd.Timestamp(payment_start_date)
    monthly_rate = float(annual_interest_rate) / 12.0

    for sequence in range(1, int(term_months) + 1):
        payment_date = _first_business_day_on_or_after(payment_anchor + pd.DateOffset(months=sequence - 1))
        beginning_principal = money(balance)
        interest_amount = money(beginning_principal * monthly_rate)
        principal_component = money(scheduled_payment - interest_amount)
        if sequence == int(term_months) or principal_component > beginning_principal:
            principal_component = money(beginning_principal)
        payment_amount = money(principal_component + interest_amount)
        ending_principal = money(beginning_principal - principal_component)
        schedule_rows.append({
            "DebtScheduleLineID": next_id(context, "DebtScheduleLine"),
            "DebtAgreementID": int(debt_agreement_id),
            "PaymentSequence": int(sequence),
            "PaymentDate": payment_date.strftime("%Y-%m-%d"),
            "BeginningPrincipal": beginning_principal,
            "PrincipalAmount": principal_component,
            "InterestAmount": interest_amount,
            "PaymentAmount": payment_amount,
            "EndingPrincipal": ending_principal,
            "JournalEntryID": None,
            "Status": "Scheduled",
        })
        balance = ending_principal

    return schedule_rows


def generate_opening_fixed_asset_records(context: GenerationContext) -> None:
    if getattr(context, "_capex_opening_records_generated", False):
        return

    item_map = capex_item_definitions()
    opening_assets = load_capex_plan()["opening_assets"]
    fixed_asset_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []

    for asset in opening_assets:
        item = item_map[str(asset["item_code"])]
        fixed_asset_id = next_id(context, "FixedAsset")
        cost_center_name_value = str(asset.get("cost_center_name") or item["cost_center_name"])
        warehouse_name_value = asset.get("warehouse_name") or item.get("warehouse_name")
        work_center_code_value = asset.get("work_center_code") or item.get("work_center_code")
        fixed_asset_rows.append({
            "FixedAssetID": fixed_asset_id,
            "AssetCode": str(asset["asset_code"]),
            "AssetDescription": str(asset["asset_description"]),
            "AssetCategory": str(item["asset_category"]),
            "BehaviorGroup": str(item["behavior_group"]),
            "ItemID": _item_id_by_code(context, str(asset["item_code"])),
            "AssetAccountID": _account_id_by_number(context, str(item["asset_account_number"])),
            "AccumulatedDepreciationAccountID": _account_id_by_number(
                context,
                str(item["accumulated_depreciation_account_number"]),
            ),
            "DepreciationDebitAccountID": _account_id_by_number(context, str(item["depreciation_account_number"])),
            "CostCenterID": cost_center_id(context, cost_center_name_value),
            "WarehouseID": _warehouse_id_by_name(context, warehouse_name_value),
            "WorkCenterID": _work_center_id_by_code(context, work_center_code_value),
            "InServiceDate": str(asset["in_service_date"]),
            "UsefulLifeMonths": int(item["useful_life_months"]),
            "OriginalCost": money(float(asset["original_cost"])),
            "OpeningAccumulatedDepreciation": money(float(asset.get("opening_accumulated_depreciation", 0.0) or 0.0)),
            "ResidualValue": 0.0,
            "Status": "Active",
            "DisposalDate": None,
        })
        event_rows.append({
            "FixedAssetEventID": next_id(context, "FixedAssetEvent"),
            "FixedAssetID": fixed_asset_id,
            "EventType": "Opening",
            "EventDate": str(context.settings.fiscal_year_start),
            "Amount": money(float(asset["original_cost"])),
            "PurchaseRequisitionID": None,
            "PurchaseOrderID": None,
            "GoodsReceiptID": None,
            "PurchaseInvoiceID": None,
            "PurchaseInvoiceLineID": None,
            "DisbursementID": None,
            "DebtAgreementID": None,
            "JournalEntryID": None,
            "FinancingType": "Opening",
            "ProceedsAmount": 0.0,
            "Description": f"Opening fixed asset balance for {asset['asset_description']}",
        })

    append_rows(context, "FixedAsset", fixed_asset_rows)
    append_rows(context, "FixedAssetEvent", event_rows)
    setattr(context, "_capex_opening_records_generated", True)


def generate_month_capex_activity(context: GenerationContext, year: int, month: int) -> None:
    generated_months = getattr(context, "_generated_capex_months", set())
    month_key = (int(year), int(month))
    if month_key in generated_months:
        return

    item_map = capex_item_definitions()
    events = [
        dict(event)
        for event in capex_plan_events()
        if pd.Timestamp(event["event_date"]).year == int(year)
        and pd.Timestamp(event["event_date"]).month == int(month)
    ]
    if not events:
        generated_months.add(month_key)
        setattr(context, "_generated_capex_months", generated_months)
        return

    requisition_rows: list[dict[str, Any]] = []
    purchase_order_rows: list[dict[str, Any]] = []
    purchase_order_line_rows: list[dict[str, Any]] = []
    receipt_rows: list[dict[str, Any]] = []
    receipt_line_rows: list[dict[str, Any]] = []
    invoice_rows: list[dict[str, Any]] = []
    invoice_line_rows: list[dict[str, Any]] = []
    disbursement_rows: list[dict[str, Any]] = []
    fixed_asset_rows: list[dict[str, Any]] = []
    fixed_asset_event_rows: list[dict[str, Any]] = []
    debt_agreement_rows: list[dict[str, Any]] = []
    debt_schedule_rows: list[dict[str, Any]] = []

    for event in sorted(events, key=lambda row: (row["event_date"], row["event_code"])):
        event_type = str(event["event_type"])
        event_date = pd.Timestamp(event["event_date"])

        if event_type == "Disposal":
            fixed_asset_id = _asset_id_by_code(context, str(event["source_asset_code"]))
            _mark_asset_disposed(context, fixed_asset_id, event_date.strftime("%Y-%m-%d"))
            fixed_asset_event_rows.append({
                "FixedAssetEventID": next_id(context, "FixedAssetEvent"),
                "FixedAssetID": fixed_asset_id,
                "EventType": "Disposal",
                "EventDate": event_date.strftime("%Y-%m-%d"),
                "Amount": 0.0,
                "PurchaseRequisitionID": None,
                "PurchaseOrderID": None,
                "GoodsReceiptID": None,
                "PurchaseInvoiceID": None,
                "PurchaseInvoiceLineID": None,
                "DisbursementID": None,
                "DebtAgreementID": None,
                "JournalEntryID": None,
                "FinancingType": "None",
                "ProceedsAmount": money(float(event.get("proceeds_amount", 0.0) or 0.0)),
                "Description": str(event["asset_description"]),
            })
            continue

        item = item_map[str(event["item_code"])]
        quantity = qty(float(event.get("quantity", 1.0) or 1.0))
        line_total = money(float(event["original_cost"]))
        unit_cost = money(line_total / float(max(quantity, 1.0)))
        financing_type = str(event.get("financing_type", "Cash"))
        dates = _capex_dates(event_date)
        cost_center_name_value = str(event.get("cost_center_name") or item["cost_center_name"])
        warehouse_name_value = event.get("warehouse_name") or item.get("warehouse_name")
        work_center_code_value = event.get("work_center_code") or item.get("work_center_code")
        supplier_category = str(event.get("supplier_category") or item.get("supplier_category") or "")

        requestor_id = _requestor_id(context, cost_center_name_value, dates["requisition_date"])
        purchasing_creator_id = _purchasing_creator_id(context, dates["order_date"])
        receiver_id = _warehouse_receiver_id(context, dates["receipt_date"])
        approval_employee_id = approver_id(context, line_total, dates["approved_date"])
        item_id = _item_id_by_code(context, str(event["item_code"]))
        supplier_id = _approved_supplier_id(context, supplier_category)
        requisition_id = next_id(context, "PurchaseRequisition")
        purchase_order_id = next_id(context, "PurchaseOrder")
        po_line_id = next_id(context, "PurchaseOrderLine")
        goods_receipt_id = next_id(context, "GoodsReceipt")
        receipt_line_id = next_id(context, "GoodsReceiptLine")
        purchase_invoice_id = next_id(context, "PurchaseInvoice")
        invoice_line_id = next_id(context, "PurchaseInvoiceLine")
        disbursement_id = next_id(context, "DisbursementPayment") if financing_type == "Cash" else None
        fixed_asset_id = next_id(context, "FixedAsset")
        debt_agreement_id = next_id(context, "DebtAgreement") if financing_type == "Note" else None

        requisition_rows.append({
            "RequisitionID": requisition_id,
            "RequisitionNumber": format_doc_number("PR", year, requisition_id),
            "RequestDate": dates["requisition_date"].strftime("%Y-%m-%d"),
            "RequestedByEmployeeID": requestor_id,
            "CostCenterID": cost_center_id(context, cost_center_name_value),
            "ItemID": item_id,
            "Quantity": quantity,
            "EstimatedUnitCost": unit_cost,
            "Justification": str(event["asset_description"]),
            "ApprovedByEmployeeID": approval_employee_id,
            "ApprovedDate": dates["approved_date"].strftime("%Y-%m-%d"),
            "Status": "Converted to PO",
            "SupplyPlanRecommendationID": None,
        })
        purchase_order_rows.append({
            "PurchaseOrderID": purchase_order_id,
            "PONumber": format_doc_number("PO", year, purchase_order_id),
            "OrderDate": dates["order_date"].strftime("%Y-%m-%d"),
            "SupplierID": supplier_id,
            "RequisitionID": None,
            "ExpectedDeliveryDate": dates["receipt_date"].strftime("%Y-%m-%d"),
            "Status": "Received" if financing_type == "Cash" else "Approved",
            "CreatedByEmployeeID": purchasing_creator_id,
            "ApprovedByEmployeeID": approval_employee_id,
            "OrderTotal": line_total,
        })
        purchase_order_line_rows.append({
            "POLineID": po_line_id,
            "PurchaseOrderID": purchase_order_id,
            "RequisitionID": requisition_id,
            "LineNumber": 1,
            "ItemID": item_id,
            "Quantity": quantity,
            "UnitCost": unit_cost,
            "LineTotal": line_total,
        })
        receipt_rows.append({
            "GoodsReceiptID": goods_receipt_id,
            "ReceiptNumber": format_doc_number("GR", year, goods_receipt_id),
            "ReceiptDate": dates["receipt_date"].strftime("%Y-%m-%d"),
            "PurchaseOrderID": purchase_order_id,
            "WarehouseID": _warehouse_id_by_name(context, warehouse_name_value),
            "ReceivedByEmployeeID": receiver_id,
            "Status": "Received",
        })
        receipt_line_rows.append({
            "GoodsReceiptLineID": receipt_line_id,
            "GoodsReceiptID": goods_receipt_id,
            "POLineID": po_line_id,
            "LineNumber": 1,
            "ItemID": item_id,
            "QuantityReceived": quantity,
            "ExtendedStandardCost": line_total,
        })
        invoice_rows.append({
            "PurchaseInvoiceID": purchase_invoice_id,
            "InvoiceNumber": f"V{supplier_id:04d}-{year}-{purchase_invoice_id:06d}",
            "InvoiceDate": dates["invoice_date"].strftime("%Y-%m-%d"),
            "ReceivedDate": dates["invoice_date"].strftime("%Y-%m-%d"),
            "DueDate": dates["payment_date"].strftime("%Y-%m-%d"),
            "PurchaseOrderID": purchase_order_id,
            "SupplierID": supplier_id,
            "SubTotal": line_total,
            "TaxAmount": 0.0,
            "GrandTotal": line_total,
            "Status": "Approved",
            "ApprovedByEmployeeID": approval_employee_id,
            "ApprovedDate": dates["approved_date"].strftime("%Y-%m-%d"),
        })
        invoice_line_rows.append({
            "PILineID": invoice_line_id,
            "PurchaseInvoiceID": purchase_invoice_id,
            "POLineID": po_line_id,
            "GoodsReceiptLineID": receipt_line_id,
            "AccrualJournalEntryID": None,
            "LineNumber": 1,
            "ItemID": item_id,
            "Quantity": quantity,
            "UnitCost": unit_cost,
            "LineTotal": line_total,
        })
        if disbursement_id is not None:
            disbursement_rows.append({
                "DisbursementID": disbursement_id,
                "PaymentNumber": format_doc_number("DP", year, disbursement_id),
                "PaymentDate": dates["payment_date"].strftime("%Y-%m-%d"),
                "SupplierID": supplier_id,
                "PurchaseInvoiceID": purchase_invoice_id,
                "Amount": line_total,
                "PaymentMethod": "Wire Transfer",
                "CheckNumber": None,
                "ApprovedByEmployeeID": approval_employee_id,
                "ClearedDate": dates["payment_date"].strftime("%Y-%m-%d"),
            })

        fixed_asset_rows.append({
            "FixedAssetID": fixed_asset_id,
            "AssetCode": str(event["asset_code"]),
            "AssetDescription": str(event["asset_description"]),
            "AssetCategory": str(item["asset_category"]),
            "BehaviorGroup": str(item["behavior_group"]),
            "ItemID": item_id,
            "AssetAccountID": _account_id_by_number(context, str(item["asset_account_number"])),
            "AccumulatedDepreciationAccountID": _account_id_by_number(
                context,
                str(item["accumulated_depreciation_account_number"]),
            ),
            "DepreciationDebitAccountID": _account_id_by_number(context, str(item["depreciation_account_number"])),
            "CostCenterID": cost_center_id(context, cost_center_name_value),
            "WarehouseID": _warehouse_id_by_name(context, warehouse_name_value),
            "WorkCenterID": _work_center_id_by_code(context, work_center_code_value),
            "InServiceDate": event_date.strftime("%Y-%m-%d"),
            "UsefulLifeMonths": int(event.get("useful_life_months", item["useful_life_months"])),
            "OriginalCost": line_total,
            "OpeningAccumulatedDepreciation": 0.0,
            "ResidualValue": 0.0,
            "Status": "Active",
            "DisposalDate": None,
        })
        fixed_asset_event_rows.append({
            "FixedAssetEventID": next_id(context, "FixedAssetEvent"),
            "FixedAssetID": fixed_asset_id,
            "EventType": event_type,
            "EventDate": event_date.strftime("%Y-%m-%d"),
            "Amount": line_total,
            "PurchaseRequisitionID": requisition_id,
            "PurchaseOrderID": purchase_order_id,
            "GoodsReceiptID": goods_receipt_id,
            "PurchaseInvoiceID": purchase_invoice_id,
            "PurchaseInvoiceLineID": invoice_line_id,
            "DisbursementID": disbursement_id,
            "DebtAgreementID": debt_agreement_id,
            "JournalEntryID": None,
            "FinancingType": financing_type,
            "ProceedsAmount": 0.0,
            "Description": str(event["asset_description"]),
        })

        if debt_agreement_id is not None:
            payment_start_date = str(event.get("payment_start_date") or _first_business_day_on_or_after(event_date + pd.DateOffset(months=1)).strftime("%Y-%m-%d"))
            debt_agreement_rows.append({
                "DebtAgreementID": debt_agreement_id,
                "AgreementNumber": f"NOTE-FA-{debt_agreement_id:05d}",
                "FixedAssetID": fixed_asset_id,
                "OriginationDate": dates["approved_date"].strftime("%Y-%m-%d"),
                "PrincipalAmount": line_total,
                "AnnualInterestRate": float(event["annual_interest_rate"]),
                "TermMonths": int(event["term_months"]),
                "PaymentStartDate": payment_start_date,
                "ScheduledPaymentAmount": _scheduled_payment_amount(
                    line_total,
                    float(event["annual_interest_rate"]),
                    int(event["term_months"]),
                ),
                "NotesPayableAccountID": _account_id_by_number(context, "2110"),
                "InterestExpenseAccountID": _account_id_by_number(context, "7030"),
                "Status": "Active",
            })
            debt_schedule_rows.extend(
                _build_debt_schedule(
                    context,
                    debt_agreement_id,
                    payment_start_date,
                    line_total,
                    float(event["annual_interest_rate"]),
                    int(event["term_months"]),
                )
            )

    append_rows(context, "PurchaseRequisition", requisition_rows)
    append_rows(context, "PurchaseOrder", purchase_order_rows)
    append_rows(context, "PurchaseOrderLine", purchase_order_line_rows)
    append_rows(context, "GoodsReceipt", receipt_rows)
    append_rows(context, "GoodsReceiptLine", receipt_line_rows)
    append_rows(context, "PurchaseInvoice", invoice_rows)
    append_rows(context, "PurchaseInvoiceLine", invoice_line_rows)
    append_rows(context, "DisbursementPayment", disbursement_rows)
    append_rows(context, "FixedAsset", fixed_asset_rows)
    append_rows(context, "FixedAssetEvent", fixed_asset_event_rows)
    append_rows(context, "DebtAgreement", debt_agreement_rows)
    append_rows(context, "DebtScheduleLine", debt_schedule_rows)
    update_purchase_order_statuses(context)
    update_purchase_invoice_statuses(context)

    generated_months.add(month_key)
    setattr(context, "_generated_capex_months", generated_months)


def generate_capex_history_through(context: GenerationContext, year: int, month: int) -> None:
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    current = pd.Timestamp(year=fiscal_start.year, month=fiscal_start.month, day=1)
    target = pd.Timestamp(year=year, month=month, day=1)
    while current <= target:
        generate_month_capex_activity(context, int(current.year), int(current.month))
        current = current + pd.DateOffset(months=1)
