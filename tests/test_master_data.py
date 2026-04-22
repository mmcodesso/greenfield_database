from generator_dataset.accrual_catalog import ACCRUAL_SERVICE_ITEMS
from generator_dataset.fixed_assets import capex_item_count
from generator_dataset.manufacturing import generate_boms
from generator_dataset.master_data import (
    DESIGN_SERVICE_COST_CENTER,
    DESIGN_SERVICE_ITEMS,
    DESIGN_SERVICE_JOB_TITLES,
    DESIGN_SERVICE_SEGMENT,
    backfill_cost_center_managers,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from generator_dataset.schema import create_empty_tables
from generator_dataset.settings import initialize_context, load_settings


def build_context():
    context = initialize_context(load_settings("config/settings.yaml"))
    create_empty_tables(context)
    return context


def test_load_accounts_uses_configured_chart() -> None:
    context = build_context()

    load_accounts(context, "config/accounts.csv")

    assert len(context.tables["Account"]) == 102
    assert context.tables["Account"]["AccountNumber"].is_unique
    assert context.counters["Account"] == 103


def test_generate_phase1_master_data() -> None:
    context = build_context()

    generate_cost_centers(context)
    load_accounts(context, "config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)

    assert len(context.tables["CostCenter"]) == 10
    assert len(context.tables["Employee"]) == context.settings.employee_count
    assert len(context.tables["Warehouse"]) == context.settings.warehouse_count
    assert context.tables["CostCenter"]["ManagerID"].notna().all()
    assert context.tables["Warehouse"]["ManagerID"].notna().all()
    assert context.tables["CostCenter"]["CostCenterName"].eq(DESIGN_SERVICE_COST_CENTER).any()
    assert set(DESIGN_SERVICE_JOB_TITLES).issubset(set(context.tables["Employee"]["JobTitle"].astype(str)))


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

    assert len(context.tables["Item"]) == (
        context.settings.item_count
        + len(DESIGN_SERVICE_ITEMS)
        + len(ACCRUAL_SERVICE_ITEMS)
        + capex_item_count()
    )
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
    assert context.tables["Customer"]["CustomerSegment"].eq(DESIGN_SERVICE_SEGMENT).any()

    service_item_codes = {item["ItemCode"] for item in DESIGN_SERVICE_ITEMS}
    design_service_items = context.tables["Item"][context.tables["Item"]["ItemCode"].isin(service_item_codes)].copy()
    assert len(design_service_items) == len(DESIGN_SERVICE_ITEMS)
    assert design_service_items["ItemGroup"].eq("Services").all()
    assert design_service_items["ItemType"].eq("Service").all()
    assert design_service_items["UnitOfMeasure"].eq("Hour").all()
    assert design_service_items["RevenueAccountID"].notna().all()
    assert design_service_items["InventoryAccountID"].isna().all()
    assert design_service_items["COGSAccountID"].isna().all()
