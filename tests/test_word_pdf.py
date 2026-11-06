"""Tests for the Windows Word converter (task #73). A fake Word only: pywin32 is never loaded."""

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from resume_optimizer import word_pdf


class FakeDocument:
    def __init__(self, app: "FakeApp", save_raises: bool) -> None:
        self.app = app
        self.save_raises = save_raises
        self.saved_to: str | None = None

    def SaveAs2(self, **kwargs: Any) -> None:  # noqa: N802 - the COM name
        if self.save_raises:
            raise RuntimeError("save failed")
        self.saved_to = kwargs["FileName"]
        assert kwargs["FileFormat"] == 17

    def Close(self, **kwargs: Any) -> None:  # noqa: N802
        self.app.closed.append(kwargs)


class FakeDocuments:
    def __init__(self, app: "FakeApp") -> None:
        self.app = app

    @property
    def Count(self) -> int:  # noqa: N802
        return self.app.other_documents

    def Open(self, **kwargs: Any) -> FakeDocument:  # noqa: N802
        if self.app.open_raises:
            raise RuntimeError("open failed")
        self.app.open_kwargs = kwargs
        return FakeDocument(self.app, self.app.save_raises)


class FakeApp:
    def __init__(
        self,
        *,
        other_documents: int = 0,
        visible: bool = False,
        open_raises: bool = False,
        save_raises: bool = False,
    ) -> None:
        self.other_documents = other_documents
        self.Visible = visible
        self.open_raises = open_raises
        self.save_raises = save_raises
        self.Documents = FakeDocuments(self)
        self.closed: list[dict[str, Any]] = []
        self.quits: list[dict[str, Any]] = []
        self.open_kwargs: dict[str, Any] = {}
        self.AutomationSecurity: int | None = None
        self.DisplayAlerts: int | None = None

    def Quit(self, **kwargs: Any) -> None:  # noqa: N802
        self.quits.append(kwargs)


def test_convert_closes_only_its_own_document_and_never_quits() -> None:
    """A successful save closes the document with SaveChanges=0 and leaves Word running."""
    app = FakeApp()
    word_pdf.convert(app, "in.docx", "out.pdf")
    assert app.closed == [{"SaveChanges": 0}]
    assert app.quits == []
    assert app.open_kwargs["FileName"] == "in.docx"
    assert app.open_kwargs["ReadOnly"] is True
    assert app.open_kwargs["Visible"] is False
    assert app.open_kwargs["AddToRecentFiles"] is False
    assert app.open_kwargs["ConfirmConversions"] is False


def test_convert_closes_the_document_when_the_save_raises() -> None:
    """The error propagates, and the document is still closed."""
    app = FakeApp(save_raises=True)
    with pytest.raises(RuntimeError, match="save failed"):
        word_pdf.convert(app, "in.docx", "out.pdf")
    assert app.closed == [{"SaveChanges": 0}]
    assert app.quits == []


def test_convert_closes_nothing_when_the_open_raises() -> None:
    """With no document there is nothing to close."""
    app = FakeApp(open_raises=True)
    with pytest.raises(RuntimeError, match="open failed"):
        word_pdf.convert(app, "in.docx", "out.pdf")
    assert app.closed == []
    assert app.quits == []


@pytest.mark.parametrize(
    ("other_documents", "visible", "expected_quits"),
    [(1, False, 0), (0, False, 1), (0, True, 0)],
)
def test_quit_if_unused(other_documents: int, visible: bool, expected_quits: int) -> None:
    """Word is quit only when nothing else is open in it and it is hidden."""
    app = FakeApp(other_documents=other_documents, visible=visible)
    assert word_pdf._quit_if_unused(app) is bool(expected_quits)
    assert app.quits == [{"SaveChanges": 0}] * expected_quits


def _pids(*sequence: set[int]) -> Any:
    """A process lister that returns each given set in turn, then repeats the last."""
    remaining = list(sequence)

    def lister() -> set[int]:
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return lister


def test_run_success_quits_once_and_records_the_new_word(tmp_path: Path) -> None:
    """With exactly one new id, the pid file holds its digits and alerts are off."""
    app = FakeApp()
    pid_file = tmp_path / "word.pid"
    code = word_pdf.run(
        "in.docx", "out.pdf", str(pid_file), lambda name: app, _pids({1, 2}, {1, 2, 77})
    )
    assert code == 0
    assert pid_file.read_bytes() == b"77"
    assert not (tmp_path / "word.pid.tmp").exists()
    assert app.AutomationSecurity == 3
    assert app.DisplayAlerts == 0
    assert app.quits == [{"SaveChanges": 0}]


@pytest.mark.parametrize("after", [{1}, {1, 77, 78}])
def test_run_writes_no_pid_file_unless_exactly_one_new_id(tmp_path: Path, after: set[int]) -> None:
    """With none, or more than one, no file is written and alerts are left alone."""
    app = FakeApp()
    pid_file = tmp_path / "word.pid"
    code = word_pdf.run("in.docx", "out.pdf", str(pid_file), lambda name: app, _pids({1}, after))
    assert code == 0
    assert not pid_file.exists()
    assert app.AutomationSecurity == 3
    assert app.DisplayAlerts is None


def test_run_with_another_document_open_never_quits(tmp_path: Path) -> None:
    """A Word with someone else's document in it is left running."""
    app = FakeApp(other_documents=1)
    code = word_pdf.run(
        "in.docx", "out.pdf", str(tmp_path / "word.pid"), lambda name: app, _pids({1})
    )
    assert code == 0
    assert app.quits == []


def test_run_quits_once_when_convert_raises(tmp_path: Path) -> None:
    """A failed conversion returns 1 and still applies the quit rule once."""
    app = FakeApp(save_raises=True)
    code = word_pdf.run(
        "in.docx", "out.pdf", str(tmp_path / "word.pid"), lambda name: app, _pids({1})
    )
    assert code == 1
    assert app.quits == [{"SaveChanges": 0}]


def test_run_quits_once_when_the_second_list_pids_raises(tmp_path: Path) -> None:
    """A failure between `dispatch_ex` and `convert` still applies the quit rule."""
    app = FakeApp()
    calls: list[int] = []

    def lister() -> set[int]:
        calls.append(1)
        if len(calls) == 2:
            raise OSError("enumeration failed")
        return {1}

    code = word_pdf.run("in.docx", "out.pdf", str(tmp_path / "w.pid"), lambda name: app, lister)
    assert code == 1
    assert app.quits == [{"SaveChanges": 0}]


def test_run_quits_once_when_the_pid_write_raises(tmp_path: Path) -> None:
    """An unwritable pid file returns 1 and still applies the quit rule."""
    app = FakeApp()
    missing_dir = tmp_path / "missing" / "word.pid"
    code = word_pdf.run(
        "in.docx", "out.pdf", str(missing_dir), lambda name: app, _pids({1}, {1, 5})
    )
    assert code == 1
    assert app.quits == [{"SaveChanges": 0}]


class RaisingOnSet(FakeApp):
    """A Word whose property refuses to be set, once armed."""

    refuse: str | None = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == self.refuse:
            raise RuntimeError(f"cannot set {name}")
        super().__setattr__(name, value)


@pytest.mark.parametrize("attribute", ["AutomationSecurity", "DisplayAlerts"])
def test_run_quits_once_when_a_setting_raises(tmp_path: Path, attribute: str) -> None:
    """A Word that refuses a setting returns 1 and still applies the quit rule."""
    app = RaisingOnSet()
    app.refuse = attribute
    code = word_pdf.run(
        "in.docx", "out.pdf", str(tmp_path / "w.pid"), lambda name: app, _pids({1}, {1, 5})
    )
    assert code == 1
    assert app.quits == [{"SaveChanges": 0}]


def test_run_returns_1_without_quitting_when_dispatch_raises(tmp_path: Path) -> None:
    """With no application there is nothing to quit."""

    def dispatch(name: str) -> Any:
        raise OSError("no word")

    assert word_pdf.run("in.docx", "out.pdf", str(tmp_path / "w.pid"), dispatch, _pids({1})) == 1


def test_run_returns_1_when_the_first_list_pids_raises(tmp_path: Path) -> None:
    """A failing first listing never reaches `dispatch_ex`."""

    def lister() -> set[int]:
        raise OSError("enumeration failed")

    def dispatch(name: str) -> Any:
        raise AssertionError("must not start Word")

    assert word_pdf.run("in.docx", "out.pdf", str(tmp_path / "w.pid"), dispatch, lister) == 1


def test_main_passes_dispatchex_and_the_lister_to_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main` uses `DispatchEx` (never `Dispatch`, which the stand-in does not have)."""

    def dispatch_ex(name: str) -> None:
        return None

    client = types.ModuleType("win32com.client")
    client.DispatchEx = dispatch_ex  # type: ignore[attr-defined]
    package = types.ModuleType("win32com")
    package.client = client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "win32com", package)
    monkeypatch.setitem(sys.modules, "win32com.client", client)
    seen: list[tuple[Any, ...]] = []

    def recorder(*args: Any) -> int:
        seen.append(args)
        return 0

    monkeypatch.setattr(word_pdf, "run", recorder)
    assert word_pdf.main(["a.docx", "a.pdf", "word.pid"]) == 0
    assert seen == [("a.docx", "a.pdf", "word.pid", dispatch_ex, word_pdf._word_pids)]
