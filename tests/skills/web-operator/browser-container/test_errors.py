"""T1: engine exceptions map to the distinguishable error contract."""

from app.engine.act import ElementNotFound, NavigationError, StaleElement
from app.engine.cdp_client import CDPError
from app.rest import errors


def test_classify_element_errors():
    assert errors.classify(ElementNotFound("x")).error_type == "not-found"
    assert errors.classify(StaleElement("x")).error_type == "stale"
    assert errors.classify(NavigationError("x")).error_type == "nav-failed"


def test_classify_cdp_timeout_vs_generic():
    assert errors.classify(CDPError("CDP timeout: DOM.resolveNode")).error_type == "timeout"
    assert errors.classify(CDPError("some other failure")).error_type == "cdp-error"


def test_status_codes_distinct():
    assert errors.classify(StaleElement("x")).status_code == 409
    assert errors.classify(NavigationError("x")).status_code == 502
    assert errors.classify(CDPError("CDP timeout: x")).status_code == 504
