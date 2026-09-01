import logging

from customer360.common.logging import configure_logging


def test_configure_logging_accepts_known_level() -> None:
    configure_logging("DEBUG")

    assert logging.getLogger().isEnabledFor(logging.DEBUG)


def test_configure_logging_falls_back_for_unknown_level() -> None:
    configure_logging("not-a-level")

    assert logging.getLogger().isEnabledFor(logging.INFO)
