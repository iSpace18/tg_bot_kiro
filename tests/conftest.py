"""
Pytest configuration and fixtures for VPN bot tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require real x-ui database"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring real x-ui database"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests without external dependencies"
    )
    config.addinivalue_line(
        "markers", "pbt: Property-based tests using Hypothesis"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="Integration tests skipped (use --run-integration to run)"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
