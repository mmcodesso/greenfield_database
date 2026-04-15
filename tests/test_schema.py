from generator_dataset.schema import TABLE_COLUMNS, create_empty_tables
from generator_dataset.settings import initialize_context, load_settings


def test_create_empty_tables_registers_all_tables() -> None:
    context = initialize_context(load_settings("config/settings.yaml"))

    create_empty_tables(context)

    assert set(context.tables) == set(TABLE_COLUMNS)
    assert set(context.counters) == set(TABLE_COLUMNS)
    assert context.tables["Account"].columns.tolist() == TABLE_COLUMNS["Account"]
    assert context.counters["Account"] == 1
