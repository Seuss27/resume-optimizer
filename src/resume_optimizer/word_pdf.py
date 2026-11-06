"""Converts a `.docx` to PDF with Word on Windows (plan §3.9, task #73).

Run as a child process: `python -I -m resume_optimizer.word_pdf SOURCE PDF PIDFILE`.

Unlike `docx2pdf`, this starts a new Word with `DispatchEx` rather than `Dispatch` (which attaches
to a running one), closes only its own document, and quits Word only when nothing else is open in
it. Word is launched by COM with the user's logon environment, not the scrubbed converter one.

It imports nothing from pywin32 at module level, so it imports on every OS, and `run` takes its
collaborators as arguments so tests never load pywin32.
"""

import contextlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_WORD_IMAGE: str = "WINWORD.EXE"
_PDF_FORMAT: int = 17  # wdFormatPDF
_FORCE_DISABLE_MACROS: int = 3  # msoAutomationSecurityForceDisable


def _word_pids() -> set[int]:
    """Lists the ids of running Word processes, by executable name. No shell, no `tasklist`."""
    import pywintypes
    import win32api
    import win32con
    import win32process

    access: int = win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ
    found: set[int] = set()
    for pid in win32process.EnumProcesses():
        try:
            handle = win32api.OpenProcess(access, False, pid)
        except pywintypes.error:
            continue
        try:
            name: str = win32process.GetModuleFileNameEx(handle, 0)
            if Path(name).name.upper() == _WORD_IMAGE:
                found.add(pid)
        except pywintypes.error:
            continue
        finally:
            win32api.CloseHandle(handle)
    return found


def _quit_if_unused(app: Any) -> bool:
    """Quits Word only when no document is open in it and it is hidden. Returns whether it did."""
    if app.Documents.Count == 0 and not app.Visible:
        app.Quit(SaveChanges=0)
        return True
    return False


def convert(app: Any, source: str, pdf: str) -> None:
    """Opens `source` read-only and hidden, saves it as a PDF, and closes only that document.

    Never quits Word. Any error propagates.
    """
    doc: Any = None
    try:
        doc = app.Documents.Open(
            FileName=source,
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        doc.SaveAs2(FileName=pdf, FileFormat=_PDF_FORMAT)
    finally:
        if doc is not None:
            doc.Close(SaveChanges=0)


def run(
    source: str,
    pdf: str,
    pid_file: str,
    dispatch_ex: Callable[[str], Any],
    list_pids: Callable[[], set[int]],
) -> int:
    """Converts one document and returns an exit code: 0 on success, 1 on any failure.

    When exactly one new Word process appeared, its id is written to `pid_file` (so the caller
    can kill it on a timeout) and alerts are turned off, since that instance is this run's own.
    Prints nothing that names the document.
    """
    try:
        before: set[int] = list_pids()
        app: Any = dispatch_ex("Word.Application")
        try:
            new: set[int] = list_pids() - before
            own: bool = len(new) == 1
            if own:
                tmp: str = f"{pid_file}.tmp"
                Path(tmp).write_bytes(str(next(iter(new))).encode("ascii"))
                os.replace(tmp, pid_file)
            # Force-disables macros in files opened programmatically on this instance. It does
            # not affect files the user opens, and only ever tightens, so any instance is safe.
            app.AutomationSecurity = _FORCE_DISABLE_MACROS
            if own:
                app.DisplayAlerts = 0
            convert(app, source, pdf)
        finally:
            with contextlib.suppress(Exception):
                _quit_if_unused(app)
    except Exception:  # noqa: BLE001 - any failure is exit code 1; the caller reports it
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Entry point: `SOURCE PDF PIDFILE`. Uses `DispatchEx`, never `Dispatch` (attaches to Word)."""
    import win32com.client

    return run(argv[0], argv[1], argv[2], win32com.client.DispatchEx, _word_pids)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
