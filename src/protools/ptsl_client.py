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


class PTSLClient:
    """Owns the PTSL Engine connection for the app.

    One instance per workflow; not thread-safe (the queue is strictly serial).
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._engine: Optional[Engine] = None

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
        return self._engine

    def invalidate(self) -> None:
        """Drop the cached engine; the next engine() call reconnects."""
        if self._engine is not None:
            try:
                self._engine.close()
            except Exception:
                pass  # channel may already be dead
            self._engine = None
            logger.info("PTSL engine invalidated; will reconnect on next use")

    def is_endpoint_up(self) -> bool:
        """Probe the PTSL endpoint without keeping a connection."""
        if self._engine is not None:
            # We think we're connected - verify with a lightweight command.
            try:
                with self.translate_errors():
                    self._engine.ptsl_version()
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
                raise SessionBlockedError(
                    "PTSL reports no open session - either no session is open "
                    "or a modal dialog is blocking Pro Tools"
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
