import pytest

from src.utils.exceptions import IngestionError, DispatchError, ConfigError
from src.utils.logger import get_logger

# Assuming retry logic is baked directly or via tenacity natively imported inside functions.
# We map directly to tests ensuring exception hierarchy enforces .retryable flag correctly.

def test_exception_retryable_flag():
    # Ingestion errors should be retryable natively
    err = IngestionError("Test")
    assert err.retryable is True
    
    # Config errors are never retryable
    cfg_err = ConfigError("Test")
    assert cfg_err.retryable is False
    
    # Dispatch error default depends on args
    dsp_err = DispatchError("Test")
    assert dsp_err.retryable is False
    
    # Overridable
    dsp_err_retry = DispatchError("Test", retryable=True)
    assert dsp_err_retry.retryable is True
