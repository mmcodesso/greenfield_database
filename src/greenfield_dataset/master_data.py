from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from faker import Faker
except ModuleNotFoundError:
    Faker = None

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, next_id


COST_CENTER_ROWS = [
    ("Executive", None, 1),
    ("Sales", None, 1),
    ("Warehouse", None, 1),
    ("Manufacturing", None, 1),
    ("Purchasing", None, 1),
    ("Administration", None, 1),
    ("Customer Service", None, 1),
    ("Research and Development", None, 1),
    ("Marketing", None, 1),
]

JOB_TITLES_BY_COST_CENTER = {
    "Executive": ["Chief Executive Officer", "Chief Financial Officer", "Controller"],
    "Sales": ["Sales Manager", "Account Executive", "Sales Representative"],
    "Warehouse": ["Warehouse Manager", "Inventory Specialist", "Shipping Clerk"],
    "Manufacturing": [
        "Production Manager",
        "Production Supervisor",
        "Production Planner",
        "Assembler",
        "Machine Operator",
        "Quality Technician",
    ],
    "Purchasing": ["Purchasing Manager", "Buyer", "Procurement Analyst"],
    "Administration": ["Accounting Manager", "Staff Accountant", "Administrative Specialist"],
    "Customer Service": ["Customer Service Manager", "Customer Service Representative"],
    "Research and Development": ["Product Analyst", "Design Coordinator"],
    "Marketing": ["Marketing Manager", "Marketing Specialist"],
}

APPROVAL_LIMITS = {
    "Staff": 0.0,
    "Supervisor": 5000.0,
    "Manager": 25000.0,
    "Executive": 250000.0,
}

ANNUAL_SALARY_BY_LEVEL = {
    "Staff": 54000.0,
    "Supervisor": 78000.0,
    "Manager": 115000.0,
    "Executive": 210000.0,
}

COST_CENTER_SALARY_MULTIPLIERS = {
    "Executive": 1.15,
    "Sales": 1.05,
    "Warehouse": 0.90,
    "Manufacturing": 0.96,
    "Purchasing": 1.00,
    "Administration": 1.00,
    "Customer Service": 0.88,
    "Research and Development": 1.10,
    "Marketing": 1.08,
}

HOURLY_TITLE_RANGES = {
    "Shipping Clerk": (20.0, 26.0),
    "Inventory Specialist": (22.0, 29.0),
    "Assembler": (22.0, 30.0),
    "Machine Operator": (24.0, 32.0),
    "Quality Technician": (25.0, 33.0),
    "Customer Service Representative": (19.0, 25.0),
    "Administrative Specialist": (21.0, 28.0),
}

STANDARD_LABOR_HOURS_RANGE = {
    "Furniture": (1.10, 2.25),
    "Lighting": (0.60, 1.35),
    "Textiles": (0.75, 1.55),
    "Accessories": (0.35, 0.85),
}

STANDARD_LABOR_RATE_RANGE = {
    "Furniture": (26.0, 32.0),
    "Lighting": (24.0, 30.0),
    "Textiles": (23.0, 28.0),
    "Accessories": (22.0, 27.0),
}

VARIABLE_OVERHEAD_RATE_RANGE = {
    "Furniture": (0.32, 0.48),
    "Lighting": (0.28, 0.44),
    "Textiles": (0.26, 0.40),
    "Accessories": (0.22, 0.36),
}

FIXED_OVERHEAD_RATE_RANGE = {
    "Furniture": (0.24, 0.38),
    "Lighting": (0.20, 0.34),
    "Textiles": (0.18, 0.30),
    "Accessories": (0.16, 0.28),
}

ITEM_GROUP_CONFIG = {
    "Furniture": ("FUR", "Finished Good", "Each", "1040", "4010", "5010", (95, 850), (1.65, 2.25)),
    "Lighting": ("LGT", "Finished Good", "Each", "1040", "4020", "5020", (35, 260), (1.75, 2.45)),
    "Textiles": ("TXT", "Finished Good", "Set", "1040", "4030", "5030", (20, 180), (1.80, 2.60)),
    "Accessories": ("ACC", "Finished Good", "Each", "1040", "4040", "5040", (8, 95), (1.90, 2.80)),
    "Packaging": ("PKG", "Purchased Material", "Box", "1045", None, None, (1, 18), None),
    "Raw Materials": ("RAW", "Purchased Material", "Roll", "1045", None, None, (5, 55), None),
}

ACCRUAL_SERVICE_ITEMS = {
    "6100": {
        "ItemCode": "SRV-INS",
        "ItemName": "Insurance Service",
        "StandardCost": 4500.0,
    },
    "6140": {
        "ItemCode": "SRV-SW",
        "ItemName": "IT and Software Service",
        "StandardCost": 6000.0,
    },
    "6180": {
        "ItemCode": "SRV-PRO",
        "ItemName": "Professional Services",
        "StandardCost": 5000.0,
    },
}

MANUFACTURED_SUPPLY_MODE_PROBABILITY = {
    "Furniture": 0.62,
    "Lighting": 0.55,
    "Textiles": 0.28,
    "Accessories": 0.12,
}

PRODUCTION_LEAD_TIME_DAYS = {
    "Furniture": (5, 10),
    "Lighting": (4, 8),
    "Textiles": (3, 7),
    "Accessories": (2, 5),
}

CONVERSION_COST_RATE = {
    "Furniture": (0.22, 0.34),
    "Lighting": (0.18, 0.28),
    "Textiles": (0.14, 0.24),
    "Accessories": (0.10, 0.18),
}

MANUFACTURED_SHARE_TARGET = 0.40
MANUFACTURED_PROMOTION_PRIORITY = {
    "Furniture": 0,
    "Lighting": 1,
    "Textiles": 2,
    "Accessories": 3,
}
MANUFACTURED_DEMOTION_PRIORITY = {
    "Accessories": 0,
    "Textiles": 1,
    "Lighting": 2,
    "Furniture": 3,
}

REGIONS = {
    "Northeast": ["NY", "PA", "NJ", "MA"],
    "Midwest": ["OH", "IN", "MI", "IL", "WI"],
    "South": ["KY", "TN", "GA", "NC", "FL"],
    "West": ["CA", "WA", "OR", "CO", "AZ"],
}


class SimpleFaker:
    def __init__(self) -> None:
        self.index = 0

    def seed_instance(self, seed: int) -> None:
        self.index = seed % 1000

    def name(self) -> str:
        self.index += 1
        return f"Employee {self.index:03d}"

    def company(self) -> str:
        self.index += 1
        suffixes = ["LLC", "Inc.", "Company", "Group", "Partners"]
        return f"Greenfield Counterparty {self.index:03d} {suffixes[self.index % len(suffixes)]}"

    def street_address(self) -> str:
        self.index += 1
        return f"{100 + self.index} Market Street"

    def city(self) -> str:
        cities = ["Cincinnati", "Columbus", "Indianapolis", "Louisville", "Pittsburgh"]
        self.index += 1
        return cities[self.index % len(cities)]

    def state_abbr(self) -> str:
        states = ["OH", "IN", "KY", "PA", "MI"]
        self.index += 1
        return states[self.index % len(states)]

    def postcode(self) -> str:
        self.index += 1
        return f"{40000 + self.index:05d}"

    def phone_number(self) -> str:
        self.index += 1
        return f"555-01{self.index % 100:02d}"

    def company_email(self) -> str:
        self.index += 1
        return f"contact{self.index:03d}@example.com"

    def date_between(self, start_date: str, end_date: str) -> pd.Timestamp:
        self.index += 1
        return pd.Timestamp("2018-01-01") + pd.Timedelta(days=self.index % 1800)


def make_faker(seed: int):
    fake = Faker("en_US") if Faker is not None else SimpleFaker()
    fake.seed_instance(seed)
    return fake


def account_id_by_number(context: GenerationContext, account_number: str | None) -> int | None:
    if account_number is None:
        return None

    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str) == account_number, "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def choose(rng, values: list, probabilities: list[float] | None = None):
    if probabilities is None:
        return values[int(rng.integers(0, len(values)))]
    return values[int(rng.choice(len(values), p=probabilities))]


def manufacturing_cost_profile(seed: int, item_group: str) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    labor_hours = money(rng.uniform(*STANDARD_LABOR_HOURS_RANGE[item_group]))
    labor_rate = money(rng.uniform(*STANDARD_LABOR_RATE_RANGE[item_group]))
    direct_labor_cost = money(labor_hours * labor_rate)
    variable_overhead_cost = money(direct_labor_cost * rng.uniform(*VARIABLE_OVERHEAD_RATE_RANGE[item_group]))
    fixed_overhead_cost = money(direct_labor_cost * rng.uniform(*FIXED_OVERHEAD_RATE_RANGE[item_group]))
    standard_conversion_cost = money(direct_labor_cost + variable_overhead_cost + fixed_overhead_cost)
    lead_low, lead_high = PRODUCTION_LEAD_TIME_DAYS[item_group]
    production_lead_time_days = int(rng.integers(lead_low, lead_high + 1))
    return {
        "ProductionLeadTimeDays": production_lead_time_days,
        "StandardLaborHoursPerUnit": labor_hours,
        "StandardDirectLaborCost": direct_labor_cost,
        "StandardVariableOverheadCost": variable_overhead_cost,
        "StandardFixedOverheadCost": fixed_overhead_cost,
        "StandardConversionCost": standard_conversion_cost,
    }


def generate_cost_centers(context: GenerationContext) -> None:
    records = []
    for name, parent_id, is_active in COST_CENTER_ROWS:
        records.append({
            "CostCenterID": next_id(context, "CostCenter"),
            "CostCenterName": name,
            "ParentCostCenterID": parent_id,
            "ManagerID": None,
            "IsActive": is_active,
        })

    context.tables["CostCenter"] = pd.DataFrame(records, columns=TABLE_COLUMNS["CostCenter"])


def load_accounts(context: GenerationContext, accounts_path: str | Path) -> None:
    accounts = pd.read_csv(accounts_path)
    expected = TABLE_COLUMNS["Account"]

    if list(accounts.columns) != expected:
        raise ValueError(f"accounts.csv columns must be exactly: {expected}")

    if accounts["AccountNumber"].duplicated().any():
        duplicates = accounts.loc[accounts["AccountNumber"].duplicated(), "AccountNumber"].tolist()
        raise ValueError(f"Duplicate account numbers: {duplicates}")

    account_ids = set(accounts["AccountID"].astype(int))
    parent_ids = {
        int(parent_id)
        for parent_id in accounts["ParentAccountID"].dropna()
        if str(parent_id).strip() != ""
    }
    missing_parent_ids = sorted(parent_ids - account_ids)
    if missing_parent_ids:
        raise ValueError(f"Account parent IDs do not exist: {missing_parent_ids}")

    accounts["AccountID"] = accounts["AccountID"].astype(int)
    accounts["ParentAccountID"] = accounts["ParentAccountID"].apply(
        lambda value: None if pd.isna(value) or str(value).strip() == "" else int(value)
    )
    accounts["IsActive"] = accounts["IsActive"].astype(int)
    context.tables["Account"] = accounts[expected]
    context.counters["Account"] = int(accounts["AccountID"].max()) + 1


def generate_employees(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed)

    cost_centers = context.tables["CostCenter"]
    if cost_centers.empty:
        raise ValueError("Generate cost centers before employees.")

    records = []
    cost_center_names = cost_centers.set_index("CostCenterID")["CostCenterName"].to_dict()
    cost_center_ids = list(cost_center_names)

    for index in range(context.settings.employee_count):
        cost_center_id = cost_center_ids[index % len(cost_center_ids)]
        cost_center_name = cost_center_names[cost_center_id]
        employee_id = next_id(context, "Employee")

        if index < len(cost_center_ids):
            authorization_level = "Executive" if cost_center_name == "Executive" else "Manager"
        elif cost_center_name == "Executive" or index < 4:
            authorization_level = "Executive"
        elif index % 5 == 0:
            authorization_level = "Manager"
        elif index % 3 == 0:
            authorization_level = "Supervisor"
        else:
            authorization_level = "Staff"

        job_titles = JOB_TITLES_BY_COST_CENTER[cost_center_name]
        records.append({
            "EmployeeID": employee_id,
            "EmployeeName": fake.name(),
            "CostCenterID": cost_center_id,
            "JobTitle": job_titles[index % len(job_titles)],
            "Email": f"employee{employee_id:03d}@greenfield.example",
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "HireDate": fake.date_between(start_date="-12y", end_date="-1y").strftime("%Y-%m-%d"),
            "ManagerID": None,
            "IsActive": 1,
            "AuthorizationLevel": authorization_level,
            "PayClass": None,
            "BaseHourlyRate": 0.0,
            "BaseAnnualSalary": 0.0,
            "StandardHoursPerWeek": 40.0,
            "OvertimeEligible": 0,
            "MaxApprovalAmount": APPROVAL_LIMITS[authorization_level],
        })

    employees = pd.DataFrame(records, columns=TABLE_COLUMNS["Employee"])
    for row in employees.itertuples():
        seed = context.settings.random_seed + int(row.EmployeeID) * 17
        rng = np.random.default_rng(seed)
        title = str(row.JobTitle)
        cost_center_name = cost_center_names[int(row.CostCenterID)]
        if title in HOURLY_TITLE_RANGES:
            low, high = HOURLY_TITLE_RANGES[title]
            employees.loc[row.Index, "PayClass"] = "Hourly"
            employees.loc[row.Index, "BaseHourlyRate"] = money(rng.uniform(low, high))
            employees.loc[row.Index, "BaseAnnualSalary"] = 0.0
            employees.loc[row.Index, "StandardHoursPerWeek"] = 40.0
            employees.loc[row.Index, "OvertimeEligible"] = 1
        else:
            salary_base = ANNUAL_SALARY_BY_LEVEL[str(row.AuthorizationLevel)]
            multiplier = COST_CENTER_SALARY_MULTIPLIERS.get(cost_center_name, 1.0)
            employees.loc[row.Index, "PayClass"] = "Salary"
            employees.loc[row.Index, "BaseHourlyRate"] = 0.0
            employees.loc[row.Index, "BaseAnnualSalary"] = money(salary_base * multiplier * rng.uniform(0.96, 1.04))
            employees.loc[row.Index, "StandardHoursPerWeek"] = 40.0
            employees.loc[row.Index, "OvertimeEligible"] = 0
    manager_by_cost_center = (
        employees[employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
        .groupby("CostCenterID")["EmployeeID"]
        .first()
        .to_dict()
    )
    employees["ManagerID"] = employees.apply(
        lambda row: None
        if row["EmployeeID"] == manager_by_cost_center.get(row["CostCenterID"])
        else manager_by_cost_center.get(row["CostCenterID"]),
        axis=1,
    )
    context.tables["Employee"] = employees


def backfill_cost_center_managers(context: GenerationContext) -> None:
    cost_centers = context.tables["CostCenter"].copy()
    employees = context.tables["Employee"]
    if cost_centers.empty or employees.empty:
        raise ValueError("Generate cost centers and employees before manager backfill.")

    managers = (
        employees[employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
        .groupby("CostCenterID")["EmployeeID"]
        .first()
        .to_dict()
    )
    cost_centers["ManagerID"] = cost_centers["CostCenterID"].map(managers)
    context.tables["CostCenter"] = cost_centers[TABLE_COLUMNS["CostCenter"]]


def generate_warehouses(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 1)

    employees = context.tables["Employee"]
    cost_centers = context.tables["CostCenter"]
    if employees.empty:
        raise ValueError("Generate employees before warehouses.")
    if cost_centers.empty:
        raise ValueError("Generate cost centers before warehouses.")

    warehouse_matches = cost_centers.loc[cost_centers["CostCenterName"].eq("Warehouse"), "CostCenterID"]
    warehouse_cost_center_id = int(warehouse_matches.iloc[0]) if not warehouse_matches.empty else None
    warehouse_managers = employees[
        employees["CostCenterID"].eq(warehouse_cost_center_id)
        & employees["AuthorizationLevel"].isin(["Manager", "Executive"])
    ]["EmployeeID"].tolist()
    fallback_manager = int(employees.iloc[0]["EmployeeID"])
    base_names = ["East Distribution Center", "West Distribution Center", "Central Overflow Warehouse"]

    records = []
    for index in range(context.settings.warehouse_count):
        records.append({
            "WarehouseID": next_id(context, "Warehouse"),
            "WarehouseName": base_names[index],
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "ManagerID": warehouse_managers[index % len(warehouse_managers)]
            if warehouse_managers
            else fallback_manager,
        })

    context.tables["Warehouse"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Warehouse"])


def generate_items(context: GenerationContext) -> None:
    if context.tables["Account"].empty:
        raise ValueError("Load accounts before items.")

    rng = context.rng
    group_names = list(ITEM_GROUP_CONFIG)
    group_probabilities = [0.34, 0.18, 0.17, 0.19, 0.07, 0.05]
    group_counts = {group: 0 for group in group_names}
    records = []

    for _ in range(context.settings.item_count):
        item_group = choose(rng, group_names, group_probabilities)
        group_counts[item_group] += 1
        planned_item_id = context.counters["Item"]
        prefix, item_type, unit, inventory, revenue, cogs, cost_range, markup_range = ITEM_GROUP_CONFIG[item_group]
        standard_cost = money(rng.uniform(*cost_range))
        list_price = None
        supply_mode = "Purchased"
        production_lead_time_days = 0
        standard_labor_hours = 0.0
        standard_direct_labor_cost = 0.0
        standard_variable_overhead_cost = 0.0
        standard_fixed_overhead_cost = 0.0
        standard_conversion_cost = 0.0
        if markup_range is not None:
            if rng.random() <= MANUFACTURED_SUPPLY_MODE_PROBABILITY.get(item_group, 0.0):
                supply_mode = "Manufactured"
                cost_profile = manufacturing_cost_profile(context.settings.random_seed + planned_item_id * 97, item_group)
                production_lead_time_days = int(cost_profile["ProductionLeadTimeDays"])
                standard_labor_hours = float(cost_profile["StandardLaborHoursPerUnit"])
                standard_direct_labor_cost = float(cost_profile["StandardDirectLaborCost"])
                standard_variable_overhead_cost = float(cost_profile["StandardVariableOverheadCost"])
                standard_fixed_overhead_cost = float(cost_profile["StandardFixedOverheadCost"])
                standard_conversion_cost = float(cost_profile["StandardConversionCost"])
            list_price = money(standard_cost * rng.uniform(*markup_range))

        item_id = next_id(context, "Item")
        records.append({
            "ItemID": item_id,
            "ItemCode": f"{prefix}-{group_counts[item_group]:04d}",
            "ItemName": f"{item_group} Item {group_counts[item_group]:04d}",
            "ItemGroup": item_group,
            "ItemType": item_type,
            "StandardCost": standard_cost,
            "ListPrice": list_price,
            "UnitOfMeasure": unit,
            "SupplyMode": supply_mode,
            "ProductionLeadTimeDays": production_lead_time_days,
            "StandardLaborHoursPerUnit": standard_labor_hours,
            "StandardDirectLaborCost": standard_direct_labor_cost,
            "StandardVariableOverheadCost": standard_variable_overhead_cost,
            "StandardFixedOverheadCost": standard_fixed_overhead_cost,
            "StandardConversionCost": standard_conversion_cost,
            "RoutingID": None,
            "InventoryAccountID": account_id_by_number(context, inventory),
            "RevenueAccountID": account_id_by_number(context, revenue),
            "COGSAccountID": account_id_by_number(context, cogs),
            "PurchaseVarianceAccountID": account_id_by_number(context, "5060"),
            "TaxCategory": "Taxable" if item_group not in ["Packaging", "Raw Materials"] else "Exempt",
            "IsActive": 1 if rng.random() > 0.03 else 0,
        })

    items = pd.DataFrame(records, columns=TABLE_COLUMNS["Item"])
    sellable_active_mask = items["RevenueAccountID"].notna() & items["IsActive"].eq(1)
    target_manufactured_count = int(round(int(sellable_active_mask.sum()) * MANUFACTURED_SHARE_TARGET))
    manufactured_active_mask = sellable_active_mask & items["SupplyMode"].eq("Manufactured")
    manufactured_count = int(manufactured_active_mask.sum())

    if manufactured_count > target_manufactured_count:
        candidates = items.loc[manufactured_active_mask].copy()
        candidates["Priority"] = candidates["ItemGroup"].map(MANUFACTURED_DEMOTION_PRIORITY).fillna(99)
        candidates = candidates.sort_values(["Priority", "ItemID"], ascending=[True, False])
        demote_count = manufactured_count - target_manufactured_count
        demote_ids = set(candidates.head(demote_count)["ItemID"].astype(int).tolist())
        mask = items["ItemID"].astype(int).isin(demote_ids)
        items.loc[mask, "SupplyMode"] = "Purchased"
        items.loc[mask, "ProductionLeadTimeDays"] = 0
        items.loc[mask, "StandardLaborHoursPerUnit"] = 0.0
        items.loc[mask, "StandardDirectLaborCost"] = 0.0
        items.loc[mask, "StandardVariableOverheadCost"] = 0.0
        items.loc[mask, "StandardFixedOverheadCost"] = 0.0
        items.loc[mask, "StandardConversionCost"] = 0.0
    elif manufactured_count < target_manufactured_count:
        candidates = items.loc[sellable_active_mask & items["SupplyMode"].eq("Purchased")].copy()
        candidates["Priority"] = candidates["ItemGroup"].map(MANUFACTURED_PROMOTION_PRIORITY).fillna(99)
        candidates = candidates.sort_values(["Priority", "ItemID"])
        promote_count = target_manufactured_count - manufactured_count
        promote_ids = candidates.head(promote_count)["ItemID"].astype(int).tolist()
        for item_id in promote_ids:
            row_index = items.index[items["ItemID"].astype(int).eq(int(item_id))][0]
            item_group = str(items.loc[row_index, "ItemGroup"])
            cost_profile = manufacturing_cost_profile(context.settings.random_seed + int(item_id) * 97, item_group)
            items.loc[row_index, "SupplyMode"] = "Manufactured"
            items.loc[row_index, "ProductionLeadTimeDays"] = int(cost_profile["ProductionLeadTimeDays"])
            items.loc[row_index, "StandardLaborHoursPerUnit"] = float(cost_profile["StandardLaborHoursPerUnit"])
            items.loc[row_index, "StandardDirectLaborCost"] = float(cost_profile["StandardDirectLaborCost"])
            items.loc[row_index, "StandardVariableOverheadCost"] = float(cost_profile["StandardVariableOverheadCost"])
            items.loc[row_index, "StandardFixedOverheadCost"] = float(cost_profile["StandardFixedOverheadCost"])
            items.loc[row_index, "StandardConversionCost"] = float(cost_profile["StandardConversionCost"])

    service_rows = []
    for account_number, service_item in ACCRUAL_SERVICE_ITEMS.items():
        service_rows.append({
            "ItemID": next_id(context, "Item"),
            "ItemCode": service_item["ItemCode"],
            "ItemName": service_item["ItemName"],
            "ItemGroup": "Services",
            "ItemType": "Service",
            "StandardCost": money(float(service_item["StandardCost"])),
            "ListPrice": None,
            "UnitOfMeasure": "Month",
            "SupplyMode": "Purchased",
            "ProductionLeadTimeDays": 0,
            "StandardLaborHoursPerUnit": 0.0,
            "StandardDirectLaborCost": 0.0,
            "StandardVariableOverheadCost": 0.0,
            "StandardFixedOverheadCost": 0.0,
            "StandardConversionCost": 0.0,
            "RoutingID": None,
            "InventoryAccountID": None,
            "RevenueAccountID": None,
            "COGSAccountID": None,
            "PurchaseVarianceAccountID": account_id_by_number(context, "5060"),
            "TaxCategory": "Exempt",
            "IsActive": 1,
        })

    if service_rows:
        items = pd.concat([items, pd.DataFrame(service_rows, columns=TABLE_COLUMNS["Item"])], ignore_index=True)

    context.tables["Item"] = items[TABLE_COLUMNS["Item"]]


def generate_customers(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 2)
    employees = context.tables["Employee"]
    cost_centers = context.tables["CostCenter"]
    if employees.empty or cost_centers.empty:
        raise ValueError("Generate employees and cost centers before customers.")

    sales_cost_center_ids = cost_centers.loc[
        cost_centers["CostCenterName"].eq("Sales"),
        "CostCenterID",
    ].tolist()
    sales_reps = employees.loc[
        employees["CostCenterID"].isin(sales_cost_center_ids),
        "EmployeeID",
    ].tolist()
    if not sales_reps:
        sales_reps = employees["EmployeeID"].tolist()

    rng = context.rng
    segments = ["Strategic", "Wholesale", "Design Trade", "Small Business"]
    segment_probabilities = [0.12, 0.38, 0.25, 0.25]
    industries = ["Hospitality", "Retail", "Office", "Real Estate", "Interior Design"]
    terms = ["Net 30", "Net 45", "Net 60", "Net 90"]
    term_probabilities = [0.45, 0.30, 0.20, 0.05]
    records = []

    for index in range(context.settings.customer_count):
        segment = choose(rng, segments, segment_probabilities)
        region = choose(rng, list(REGIONS))
        state = choose(rng, REGIONS[region])
        credit_limit = {
            "Strategic": rng.uniform(125000, 350000),
            "Wholesale": rng.uniform(50000, 175000),
            "Design Trade": rng.uniform(25000, 100000),
            "Small Business": rng.uniform(7500, 40000),
        }[segment]
        customer_id = next_id(context, "Customer")
        records.append({
            "CustomerID": customer_id,
            "CustomerName": fake.company(),
            "ContactName": fake.name(),
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": state,
            "PostalCode": fake.postcode(),
            "Country": "USA",
            "Phone": fake.phone_number(),
            "Email": f"customer{customer_id:04d}@example.com",
            "CreditLimit": money(credit_limit),
            "PaymentTerms": choose(rng, terms, term_probabilities),
            "CustomerSince": fake.date_between(start_date="-10y", end_date="-1y").strftime("%Y-%m-%d"),
            "SalesRepEmployeeID": int(choose(rng, sales_reps)),
            "CustomerSegment": segment,
            "Industry": choose(rng, industries),
            "Region": region,
            "IsActive": 1 if index < int(context.settings.customer_count * 0.96) else 0,
        })

    context.tables["Customer"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Customer"])


def generate_suppliers(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 3)
    rng = context.rng
    categories = ["Furniture", "Lighting", "Textiles", "Accessories", "Packaging", "Raw Materials", "Logistics", "Services"]
    category_probabilities = [0.20, 0.13, 0.14, 0.15, 0.10, 0.10, 0.08, 0.10]
    terms = ["Net 30", "Net 45", "Net 60"]
    risk_ratings = ["Low", "Medium", "High"]
    records = []

    for index in range(context.settings.supplier_count):
        supplier_id = next_id(context, "Supplier")
        risk_rating = choose(rng, risk_ratings, [0.68, 0.25, 0.07])
        records.append({
            "SupplierID": supplier_id,
            "SupplierName": fake.company(),
            "ContactName": fake.name(),
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "PostalCode": fake.postcode(),
            "Country": "USA",
            "Phone": fake.phone_number(),
            "Email": f"supplier{supplier_id:04d}@example.com",
            "PaymentTerms": choose(rng, terms, [0.45, 0.35, 0.20]),
            "IsApproved": 1 if index < int(context.settings.supplier_count * 0.94) else 0,
            "TaxID": f"XX-XXX{1000 + supplier_id:04d}",
            "BankAccount": f"****{5000 + supplier_id:04d}",
            "SupplierCategory": choose(rng, categories, category_probabilities),
            "SupplierRiskRating": risk_rating,
            "DefaultCurrency": "USD",
        })

    context.tables["Supplier"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Supplier"])
