from generator_dataset.budgets import generate_budgets, generate_opening_balances
from generator_dataset.main import build_phase1
from generator_dataset.master_data import generate_customers, generate_items, generate_suppliers
from generator_dataset.validations import validate_phase2


def test_generate_opening_balances_and_budgets() -> None:
    context = build_phase1()

    generate_items(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)
    results = validate_phase2(context)

    assert results["exceptions"] == []
    assert len(context.tables["JournalEntry"]) == 1
    assert len(context.tables["GLEntry"]) == 16
    assert round(context.tables["GLEntry"]["Debit"].sum(), 2) == round(context.tables["GLEntry"]["Credit"].sum(), 2)
    assert 2000 <= len(context.tables["Budget"]) <= 4500
