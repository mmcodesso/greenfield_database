from CharlesRiver_dataset.manufacturing import generate_boms
from CharlesRiver_dataset.master_data import (
    backfill_cost_center_managers,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from CharlesRiver_dataset.schema import create_empty_tables
from CharlesRiver_dataset.settings import initialize_context, load_settings


def build_context():
    context = initialize_context(load_settings("config/settings.yaml"))
    create_empty_tables(context)
    return context


def test_load_accounts_uses_configured_chart() -> None:
    context = build_context()

    load_accounts(context, "config/accounts.csv")

    assert len(context.tables["Account"]) == 98
    assert context.tables["Account"]["AccountNumber"].is_unique
    assert context.counters["Account"] == 99


def test_generate_phase1_master_data() -> None:
    context = build_context()

    generate_cost_centers(context)
    load_accounts(context, "config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)

    assert len(context.tables["CostCenter"]) == 9
    assert len(context.tables["Employee"]) == context.settings.employee_count
    assert len(context.tables["Warehouse"]) == context.settings.warehouse_count
    assert context.tables["CostCenter"]["ManagerID"].notna().all()
    assert context.tables["Warehouse"]["ManagerID"].notna().all()


def test_generate_phase2_master_data() -> None:
    context = build_context()

    generate_cost_centers(context)
    load_accounts(context, "config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    generate_items(context)
    generate_boms(context)
    generate_customers(context)
    generate_suppliers(context)

    assert len(context.tables["Item"]) == context.settings.item_count + 3
    assert len(context.tables["BillOfMaterial"]) > 0
    assert len(context.tables["BillOfMaterialLine"]) > 0
    assert len(context.tables["Customer"]) == context.settings.customer_count
    assert len(context.tables["Supplier"]) == context.settings.supplier_count
    assert context.tables["Item"]["ItemCode"].is_unique
    non_service_items = context.tables["Item"][~context.tables["Item"]["ItemGroup"].eq("Services")]
    assert non_service_items["InventoryAccountID"].notna().all()
    assert context.tables["Item"]["SupplyMode"].isin(["Purchased", "Manufactured"]).all()
    assert context.tables["Customer"]["SalesRepEmployeeID"].notna().all()
    assert context.tables["Supplier"]["DefaultCurrency"].eq("USD").all()
