"""Tests for govlink.datasets.exchange_rates.dataset — registration module."""

from __future__ import annotations

import importlib
import sys

from govlink.core.models import DatasetFrequency
from govlink.core.registry import DatasetRegistry
from govlink.datasets.exchange_rates.model import (
    ExchangeRate,
    ExchangeRateRecord,
)
from govlink.datasets.exchange_rates.parser import ExchangeRatesParser
from govlink.datasets.exchange_rates.source import ExchangeRatesSource

_DATASET_MODULE_NAME = "govlink.datasets.exchange_rates.dataset"


def _reload_dataset_module() -> None:
    """Force a single fresh import of the dataset registration module.

    The module's top-level body calls ``get_registry().register(...)``;
    that side effect is what we want to fire exactly once against the
    fresh ``isolated_global_registry``. Naively combining ``import`` +
    ``importlib.reload`` would call register twice on the first run
    (because ``import`` runs the body and ``reload`` runs it again),
    so we drop any cached copy from ``sys.modules`` first.
    """
    sys.modules.pop(_DATASET_MODULE_NAME, None)
    importlib.import_module(_DATASET_MODULE_NAME)


def test_dataset_module_registers_on_import(
    isolated_global_registry: DatasetRegistry,
) -> None:
    """Importing the dataset module re-fires its register() side effect.

    See :func:`_reload_dataset_module` for the cache-eviction trick we
    use to make the re-import deterministic. Module identity changes —
    that's fine here because we only care about the side effect.
    """
    _reload_dataset_module()
    assert "exchange-rates" in isolated_global_registry


def test_definition_has_expected_metadata(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert definition.slug == "exchange-rates"
    assert definition.title == "Daily Valuation Exchange Rates"
    assert definition.publisher == "Central Bank of The Gambia"
    assert definition.source_url == "https://www.cbg.gm/daily-valuation-exchange-rate"
    assert definition.frequency is DatasetFrequency.DAILY


def test_definition_source_is_exchange_rates_source(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert isinstance(definition.source, ExchangeRatesSource)


def test_definition_parser_is_exchange_rates_parser(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert isinstance(definition.parser, ExchangeRatesParser)


def test_definition_model_class_is_exchange_rate(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert definition.model_class is ExchangeRate


def test_definition_schema_class_is_exchange_rate_record(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert definition.schema_class is ExchangeRateRecord


def test_definition_data_table_name_matches_orm_tablename(
    isolated_global_registry: DatasetRegistry,
) -> None:
    _reload_dataset_module()
    definition = isolated_global_registry.get("exchange-rates")
    assert definition.data_table_name == ExchangeRate.__tablename__
    assert definition.data_table_name == "data_exchange_rates"
