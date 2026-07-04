"""PTSL engine lifecycle: connect/reconnect, readiness, pacing, error translation.

Wraps py-ptsl's Engine so the rest of the app never touches grpc or
ptsl error types directly. Key behaviors (see docs/DEVELOPER_IMPROVEMENT_PLAN.md §3):

- Lazy connection; a dead gRPC channel invalidates the cached engine and the
  next call reconnects, so Pro Tools restarts are survivable.
- host_ready_check() before operations (Pro Tools wedges under rapid cycling).
- settle() pauses after create/import/open (§3.3).
- Typed error translation:
    gRPC UNAVAILABLE        -> ProToolsNotRunningError
    PT_NoOpenedSession(106) -> SessionBlockedError ("no session OR modal up")
    PT_InvalidParameter(126)-> PTSLParameterError (non-retryable)
"""

import logging
import time
from contextlib import contextmanager
from typing import Optional

from src.protools import ptsl_compat  # noqa: F401  (must precede ptsl import)

import grpc
from ptsl.client import PTSL_VERSION as CLIENT_PTSL_VERSION
from ptsl.engine import Engine
from ptsl.errors import CommandError

from src.core.exceptions import (
    PTSLError,
    PTSLParameterError,
    ProToolsNotRunningError,
    SessionBlockedError,
)
from src.protools.settings import AppSettings

logger = logging.getLogger(__name__)

# PTSL CommandErrorType values (Avid PTSL SDK)
PT_NO_OPENED_SESSION = 106
PT_INVALID_PARAMETER = 126

COMPANY_NAME = "Pro Tools Prepper"
APPLICATION_NAME = "Pro Tools Session Builder"

# PTSL protocol version -> approximate Pro Tools release. The server is
# backward compatible with older clients (each request carries the client's
# version in its header), so the pin only bites when Pro Tools is OLDER
# than the bundled client.
PTSL_VERSION_RELEASES = {
    1: "2023.3",
    2: "2023.12",
    3: "2024.3",
    4: "2024.6",
    5: "2024.10",
}


def describe_ptsl_version(version: int) -> str:
    """Human-readable name for a PTSL protocol version."""
    release = PTSL_VERSION_RELEASES.get(version)
    if release:
        return f"PTSL v{version} (~Pro Tools {release})"
    return f"PTSL v{version} (newer than this build was tested with)"


class PTSLClient:
    """Owns the PTSL Engine connection for the app.

    One instance per workflow; not thread-safe (the queue is strictly serial).
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._engine: Optional[Engine] = None
        self.server_ptsl_version: Optional[int] = None

    @property
    def address(self) -> str:
        return f"localhost:{self.settings.ptsl_port}"

    # -- connection management -------------------------------------------

    def engine(self) -> Engine:
        """Return a connected Engine, connecting lazily.

        Raises:
            ProToolsNotRunningError: If the PTSL endpoint is unreachable.
        """
        if self._engine is None:
            try:
                self._engine = Engine(
                    company_name=COMPANY_NAME,
                    application_name=APPLICATION_NAME,
                    address=self.address,
                )
                logger.info("Connected to PTSL at %s", self.address)
            except grpc.RpcError as e:
                raise ProToolsNotRunningError(
                    f"Cannot reach Pro Tools PTSL endpoint at {self.address}: "
                    f"{e.code().name if hasattr(e, 'code') else e}"
                ) from e
            self._check_server_version()
        return self._engine

    def _check_server_version(self) -> None:
        """Probe the server's PTSL version and gate on "server too old".

        The server honors requests from older clients (backward compatible),
        so a NEWER Pro Tools is fine - only an older one cannot understand
        this client. The probe itself must never block connection: a modal
        dialog can make it fail (106) even though Pro Tools is healthy.

        Raises:
            PTSLError: Pro Tools is older than the bundled client supports.
        """
        try:
            self.server_ptsl_version = self._engine.ptsl_version()
        except Exception as e:
            logger.warning(
                "Could not determine Pro Tools PTSL version (%s) - "
                "proceeding without the compatibility check", e,
            )
            self.server_ptsl_version = None
            return

        if self.server_ptsl_version < CLIENT_PTSL_VERSION:
            required = PTSL_VERSION_RELEASES.get(CLIENT_PTSL_VERSION, "?")
            raise PTSLError(
                f"This app requires Pro Tools {required} or newer "
                f"(PTSL v{CLIENT_PTSL_VERSION}); this Pro Tools speaks "
                f"{describe_ptsl_version(self.server_ptsl_version)}. "
                f"Please update Pro Tools."
            )
        if self.server_ptsl_version > CLIENT_PTSL_VERSION:
            logger.info(
                "Pro Tools speaks %s - newer than this app's client "
                "(v%d). PTSL is backward compatible; proceeding.",
                describe_ptsl_version(self.server_ptsl_version),
                CLIENT_PTSL_VERSION,
            )
        else:
            logger.info(
                "Pro Tools speaks %s - matches this app's client.",
                describe_ptsl_version(self.server_ptsl_version),
            )

    def invalidate(self) -> None:
        """Drop the cached engine; the next engine() call reconnects."""
        if self._engine is not None:
            try:
                self._engine.close()
            except Exception:
                pass  # channel may already be dead
            self._engine = None
            # A reconnect may be to a different Pro Tools (e.g. after an
            # upgrade) - re-probe on next connect.
            self.server_ptsl_version = None
            logger.info("PTSL engine invalidated; will reconnect on next use")

    def is_endpoint_up(self) -> bool:
        """Probe the PTSL endpoint without keeping a connection."""
        if self._engine is not None:
            # We think we're connected - verify with a lightweight command.
            try:
                with self.translate_errors():
                    version = self._engine.ptsl_version()
                if self.server_ptsl_version is None:
                    # Connect-time probe was blocked; record it now.
                    self.server_ptsl_version = version
                    logger.info(
                        "Pro Tools speaks %s", describe_ptsl_version(version)
                    )
                return True
            except ProToolsNotRunningError:
                pass  # engine already invalidated; fall through to fresh probe
            except PTSLError:
                return True  # endpoint answered, even if with a command error
            except Exception:
                self.invalidate()
                # fall through to fresh probe
        try:
            probe = Engine(
                company_name=COMPANY_NAME,
                application_name=f"{APPLICATION_NAME} (probe)",
                address=self.address,
            )
            probe.close()
            return True
        except Exception:
            return False

    # -- pacing (§3.3: rapid command cycling can wedge Pro Tools) ---------

    def ensure_ready(self, timeout: Optional[float] = None) -> None:
        """Block until Pro Tools reports ready, with backoff.

        Raises:
            ProToolsNotRunningError: If the endpoint dies while waiting.
            PTSLError: If Pro Tools never reports ready within timeout.
        """
        deadline = time.monotonic() + (timeout if timeout is not None else 60.0)
        delay = 0.5
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            try:
                with self.translate_errors():
                    self.engine().host_ready_check()
                return
            except ProToolsNotRunningError:
                raise
            except PTSLError as e:
                last_error = e
                time.sleep(delay)
                delay = min(delay * 2, 5.0)
        raise PTSLError(f"Pro Tools did not report ready in time: {last_error}")

    def settle(self) -> None:
        """Pause after heavy operations (create/import/open) - §3.3."""
        time.sleep(self.settings.ptsl_settle_time)

    # -- error translation -------------------------------------------------

    @contextmanager
    def translate_errors(self):
        """Translate grpc/ptsl errors into the app's typed exceptions.

        A channel error invalidates the cached engine so the next call
        reconnects (Pro Tools crash/restart recovery).
        """
        try:
            yield
        except CommandError as e:
            if e.error_type == PT_NO_OPENED_SESSION:
                # Observed details: "Unable to complete..." (idle, no session),
                # "Session state is already changing" (transient - PT busy
                # starting up or mid-transition; retry after a wait).
                raise SessionBlockedError(
                    "PTSL reports no open session - no session is open, a modal "
                    f"dialog is blocking, or Pro Tools is mid-transition: {e.message}"
                ) from e
            if e.error_type == PT_INVALID_PARAMETER:
                raise PTSLParameterError(f"PTSL rejected a parameter: {e.message}") from e
            raise PTSLError(f"PTSL command failed ({e.error_name}): {e.message}") from e
        except grpc.RpcError as e:
            self.invalidate()
            code = e.code() if hasattr(e, "code") else None
            if code == grpc.StatusCode.UNAVAILABLE:
                raise ProToolsNotRunningError(
                    "Pro Tools PTSL endpoint became unavailable (crashed or quit?)"
                ) from e
            raise PTSLError(f"PTSL transport error: {code}") from e
