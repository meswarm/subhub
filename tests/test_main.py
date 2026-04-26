import logging

from subhub.main import _configure_logging


def test_configure_logging_reduces_noisy_dependencies():
    _configure_logging("INFO")

    assert logging.getLogger("nio").level == logging.WARNING
    assert logging.getLogger("nio.rooms").level == logging.WARNING
    assert logging.getLogger("httpx").level == logging.WARNING
