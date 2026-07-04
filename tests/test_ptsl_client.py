"""Tests for PTSLClient's server-version probe and compatibility gate.

The PTSL server is backward compatible with older clients (each request
carries the client's protocol version), so only "server OLDER than client"
is fatal. The probe itself must never block a connection - a modal dialog
can make it fail even though Pro Tools is healthy.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import PTSLError, SessionBlockedError
from src.protools.ptsl_client import (
    CLIENT_PTSL_VERSION,
    PTSLClient,
    PTSL_VERSION_RELEASES,
    describe_ptsl_version,
)
from src.protools.settings import AppSettings


@pytest.fixture
def client():
    return PTSLClient(AppSettings())


def connect(client, server_version):
    """Connect the client against a fake Engine reporting server_version."""
    fake_engine = MagicMock()
    if isinstance(server_version, Exception):
        fake_engine.ptsl_version.side_effect = server_version
    else:
        fake_engine.ptsl_version.return_value = server_version
    with patch("src.protools.ptsl_client.Engine", return_value=fake_engine):
        return client.engine()


class TestVersionGate:
    def test_matching_version_connects(self, client):
        engine = connect(client, CLIENT_PTSL_VERSION)
        assert engine is not None
        assert client.server_ptsl_version == CLIENT_PTSL_VERSION

    def test_newer_server_connects(self, client, caplog):
        with caplog.at_level("INFO"):
            connect(client, CLIENT_PTSL_VERSION + 2)
        assert client.server_ptsl_version == CLIENT_PTSL_VERSION + 2
        assert "backward compatible" in caplog.text

    def test_older_server_raises_readable_error(self, client):
        required = PTSL_VERSION_RELEASES[CLIENT_PTSL_VERSION]
        with pytest.raises(PTSLError, match=f"requires Pro Tools {required}"):
            connect(client, CLIENT_PTSL_VERSION - 1)

    def test_blocked_probe_does_not_block_connection(self, client, caplog):
        """A modal dialog can fail the probe (106); connection must survive."""
        with caplog.at_level("WARNING"):
            engine = connect(client, SessionBlockedError("modal up"))
        assert engine is not None
        assert client.server_ptsl_version is None
        assert "without the compatibility check" in caplog.text

    def test_invalidate_clears_cached_version(self, client):
        connect(client, CLIENT_PTSL_VERSION)
        client.invalidate()
        assert client.server_ptsl_version is None


class TestDescribeVersion:
    def test_known_version(self):
        assert describe_ptsl_version(3) == "PTSL v3 (~Pro Tools 2024.3)"

    def test_unknown_version(self):
        assert "newer than this build" in describe_ptsl_version(99)
