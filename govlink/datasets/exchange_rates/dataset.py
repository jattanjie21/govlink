"""Registration of the exchange-rates dataset.

This module is the plugin entrypoint discovered by
:meth:`govlink.core.registry.DatasetRegistry.auto_discover`. Importing
it has the side effect of registering the dataset definition on the
process-global registry. Tests that exercise the registration must use
the ``isolated_global_registry`` fixture and reload this module to
re-fire the side effect.
"""

from __future__ import annotations

from govlink.core.definition import DatasetDefinition
from govlink.core.models import DatasetFrequency
from govlink.core.registry import get_registry
from govlink.datasets.exchange_rates.model import (
    ExchangeRate,
    ExchangeRateRecord,
)
from govlink.datasets.exchange_rates.parser import ExchangeRatesParser
from govlink.datasets.exchange_rates.source import ExchangeRatesSource

definition = DatasetDefinition(
    slug="exchange-rates",
    title="Daily Valuation Exchange Rates",
    description=(
        "Official daily valuation exchange rates published by the "
        "Central Bank of The Gambia, expressed as Gambian Dalasi (GMD) "
        "per unit (or per 100 / per 5000) of foreign currency."
    ),
    publisher="Central Bank of The Gambia",
    source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
    frequency=DatasetFrequency.DAILY,
    source=ExchangeRatesSource(),
    parser=ExchangeRatesParser(),
    model_class=ExchangeRate,
    schema_class=ExchangeRateRecord,
)

get_registry().register(definition)
