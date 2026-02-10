"""Async command execution utilities."""

import asyncio
import logging
from typing import Tuple

DEFAULT_TIMEOUT = 30
UPGRADE_TIMEOUT = 300
INSTALL_TIMEOUT = 600

_logging = logging.getLogger(__name__)


async def run_command_async(
    command: str, timeout: int = DEFAULT_TIMEOUT, debug: bool = False
) -> Tuple[str, int]:
    """Run a command asynchronously and return output and return code."""
    process = None
    try:
        if debug:
            _logging.debug(f"Running command: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            output = stdout.decode().strip()
            if stderr and debug:
                _logging.debug(f"stderr: {stderr.decode().strip()}")
            return output, process.returncode if process.returncode is not None else 1
        except asyncio.TimeoutError:
            process.kill()
            _ = await process.wait()
            _logging.error(f"Command timed out after {timeout} seconds: {command}")
            return f"Command timed out after {timeout} seconds", 1
    except Exception as e:
        _logging.error(f"Command execution failed: {type(e).__name__}: {e} | Command: {command}")
        return f"Error: {str(e)}", 1
    finally:
        if process:
            transport = getattr(process, "_transport", None)
            if transport:
                transport.close()
