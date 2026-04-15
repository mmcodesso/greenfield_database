from generator_dataset.main import build_phase3
from generator_dataset.o2c import generate_month_shipments
from generator_dataset.p2p import generate_month_goods_receipts
from generator_dataset.validations import validate_phase4


def test_generate_phase4_fulfillment_and_receiving() -> None:
    context = build_phase3()

    generate_month_shipments(context, 2026, 1)
    generate_month_goods_receipts(context, 2026, 1)
    results = validate_phase4(context)

    assert results["exceptions"] == []
    assert len(context.tables["Shipment"]) > 0
    assert len(context.tables["ShipmentLine"]) >= len(context.tables["Shipment"])
    assert len(context.tables["GoodsReceipt"]) > 0
    assert len(context.tables["GoodsReceiptLine"]) >= len(context.tables["GoodsReceipt"])
    assert context.tables["Shipment"]["ShipmentNumber"].is_unique
    assert context.tables["GoodsReceipt"]["ReceiptNumber"].is_unique
    assert set(context.tables["ShipmentLine"]["ShipmentID"]).issubset(set(context.tables["Shipment"]["ShipmentID"]))
    assert set(context.tables["GoodsReceiptLine"]["GoodsReceiptID"]).issubset(set(context.tables["GoodsReceipt"]["GoodsReceiptID"]))
