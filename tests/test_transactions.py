from generator_dataset.main import build_phase2
from generator_dataset.o2c import generate_month_o2c
from generator_dataset.p2p import generate_month_p2p
from generator_dataset.validations import validate_phase3


def test_generate_phase3_monthly_transactions() -> None:
    context = build_phase2()

    generate_month_o2c(context, 2026, 1)
    generate_month_p2p(context, 2026, 1)
    results = validate_phase3(context)

    assert results["exceptions"] == []
    assert 90 <= len(context.tables["SalesOrder"]) <= 140
    assert len(context.tables["SalesOrderLine"]) > len(context.tables["SalesOrder"])
    assert 80 <= len(context.tables["PurchaseRequisition"]) <= 110
    assert len(context.tables["PurchaseOrder"]) > 0
    assert len(context.tables["PurchaseOrderLine"]) >= len(context.tables["PurchaseOrder"])
    assert context.tables["PurchaseOrderLine"]["RequisitionID"].notna().all()
    assert context.tables["SalesOrder"]["OrderNumber"].is_unique
    assert context.tables["PurchaseOrder"]["PONumber"].is_unique
