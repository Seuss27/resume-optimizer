"""A3 render safety: active-content scan, converter command, environment, real page count."""

import importlib.util
import logging
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from resume_optimizer import render
from resume_optimizer.render import PdfConversionError


def _make_docx(path: Path, document: str = "<w:document/>", rels: str = "<Relationships/>") -> Path:
    """Writes a minimal zip package with the given document and relationships parts."""
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/document.xml", document)
        package.writestr("word/_rels/document.xml.rels", rels)
    return path


def test_scan_accepts_hyperlinks_and_refuses_active_content(tmp_path: Path) -> None:
    """Contact hyperlinks pass. Fields and non-hyperlink external targets are refused."""
    link = (
        '<Relationships><Relationship Id="1" '
        'Type="http://x/relationships/hyperlink" Target="https://example.com" '
        'TargetMode="External"/></Relationships>'
    )
    assert render.scan_for_active_content(_make_docx(tmp_path / "a.docx", rels=link)) == []
    field = _make_docx(tmp_path / "b.docx", document="<w:fldSimple w:instr='X'/>")
    assert render.scan_for_active_content(field) == ["field"]
    image = (
        '<Relationships><Relationship Id="1" Type="http://x/relationships/image" '
        'Target="file://host/s/a.png" TargetMode="External"/></Relationships>'
    )
    flagged = render.scan_for_active_content(_make_docx(tmp_path / "c.docx", rels=image))
    assert flagged == ["external target"]


def test_page_count_refuses_active_content_before_converting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A document with a field is never handed to a converter."""
    docx = _make_docx(tmp_path / "a.docx", document="<w:instrText/>")

    def fail(*args: object) -> None:
        raise AssertionError("converter must not run")

    monkeypatch.setattr(render, "docx_to_pdf", fail)
    with pytest.raises(PdfConversionError, match="refused"):
        render.page_count(docx)


def test_unreadable_package_is_a_conversion_error(tmp_path: Path) -> None:
    """A file that is not a zip raises the conversion error, not a traceback."""
    bad = tmp_path / "a.docx"
    bad.write_bytes(b"not a zip")
    with pytest.raises(PdfConversionError):
        render.scan_for_active_content(bad)


def test_count_pdf_pages_reads_a_real_pdf(tmp_path: Path) -> None:
    """pypdf counts the pages of a two-page PDF built in the test."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    pdf = tmp_path / "two.pdf"
    with pdf.open("wb") as f:
        writer.write(f)
    assert render.count_pdf_pages(pdf) == 2


def test_unreadable_pdf_is_a_conversion_error(tmp_path: Path) -> None:
    """A corrupt PDF raises the conversion error."""
    bad = tmp_path / "a.pdf"
    bad.write_bytes(b"junk")
    with pytest.raises(PdfConversionError):
        render.count_pdf_pages(bad)


def test_converter_command_and_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Word is driven through an importable entry point, isolated, with no credentials."""
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")
    seen: list[list[str]] = []

    def fake_run(args: list[str], timeout: int, pid_file: Path | None = None) -> None:
        seen.append(args)
        (tmp_path / "a.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr(render, "_run", fake_run)
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    render.docx_to_pdf(docx, tmp_path)
    assert seen[0][:3] == [sys.executable, "-I", "-c"]
    assert "from docx2pdf import convert" in seen[0][3]
    assert importlib.util.find_spec("docx2pdf") is not None

    seen.clear()
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    render.docx_to_pdf(docx, tmp_path)
    pdf = str((tmp_path / "a.pdf").resolve())
    assert seen[0] == [
        sys.executable, "-I", "-m", "resume_optimizer.word_pdf",
        str(docx.resolve()), pdf, str((tmp_path / "word.pid").resolve()),
    ]  # fmt: skip

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PATH", "/bin")
    env = render._converter_env()
    assert "GEMINI_API_KEY" not in env
    assert "PATH" in env


def test_scan_refuses_media_duplicates_and_unsafe_links(tmp_path: Path) -> None:
    """Media parts, duplicate part names and non-https links are refused."""
    media = _make_docx(tmp_path / "m.docx")
    with zipfile.ZipFile(media, "a") as package:
        package.writestr("word/media/a.png", b"x")
    assert render.scan_for_active_content(media) == ["embedded media"]

    dup = tmp_path / "d.docx"
    with zipfile.ZipFile(dup, "w") as package:
        package.writestr("word/document.xml", "<w:document/>")
        with pytest.warns(UserWarning):
            package.writestr("word/document.xml", "<w:fldSimple/>")
    with pytest.raises(PdfConversionError, match="duplicate"):
        render.scan_for_active_content(dup)

    link = (
        '<Relationships><Relationship Id="1" Type="http://x/relationships/hyperlink" '
        'Target="file://host/share/a" TargetMode="External"/></Relationships>'
    )
    flagged = render.scan_for_active_content(_make_docx(tmp_path / "l.docx", rels=link))
    assert flagged == ["external target"]
    hidden = (
        '<Relationships><Relationship Id="1" Target="a>b" '
        'Type="http://x/relationships/attachedTemplate" TargetMode="External"/></Relationships>'
    )
    assert render.scan_for_active_content(_make_docx(tmp_path / "h.docx", rels=hidden)) == [
        "external target"
    ]


class _FakeChild:
    """Stands in for `subprocess.Popen`'s result."""

    pid: int = 4242

    def __init__(self, *, hang: bool = False, returncode: int = 0) -> None:
        self.hang: bool = hang
        self.returncode: int = returncode
        self.waits: list[int | None] = []
        self.killed: bool = False

    def wait(self, timeout: int | None = None) -> int:
        self.waits.append(timeout)
        if self.hang and len(self.waits) == 1:
            raise subprocess.TimeoutExpired("converter", timeout or 0)
        return self.returncode

    def kill(self) -> None:
        self.killed = True


def _install_popen(monkeypatch: pytest.MonkeyPatch, child: _FakeChild) -> dict[str, object]:
    """Replaces `Popen` on the stand-in `subprocess` and returns what it was called with."""
    seen: dict[str, object] = {}

    def fake(args: list[str], **kwargs: object) -> _FakeChild:
        seen.update(kwargs, args=args)
        return child

    monkeypatch.setattr(render.subprocess, "Popen", fake)
    return seen


def test_run_passes_no_shell_a_timeout_a_scrubbed_env_and_no_pipes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real `_run` starts the converter safely."""
    child = _FakeChild()
    seen = _install_popen(monkeypatch, child)
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    render._run(["tool", "arg"], 7)
    assert seen["args"] == ["tool", "arg"]
    assert child.waits == [7]
    assert "shell" not in seen
    assert seen["start_new_session"] is True
    assert seen["stdin"] is render.subprocess.DEVNULL
    assert seen["stdout"] is render.subprocess.DEVNULL
    assert seen["stderr"] is render.subprocess.DEVNULL
    assert "GEMINI_API_KEY" not in seen["env"]  # type: ignore[operator]


def test_run_raises_on_a_non_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing converter raises `CalledProcessError`."""
    _install_popen(monkeypatch, _FakeChild(returncode=3))
    with pytest.raises(subprocess.CalledProcessError):
        render._run(["tool"], 7)


def test_run_does_not_start_a_session_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """`start_new_session` is a POSIX option."""
    seen = _install_popen(monkeypatch, _FakeChild())
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    render._run(["tool"], 7)
    assert "start_new_session" not in seen


def _record_kills(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, str | None]]:
    kills: list[tuple[int, str | None]] = []

    def fake_kill(pid: int, image: str | None = None) -> None:
        kills.append((pid, image))

    monkeypatch.setattr(render, "_kill_tree", fake_kill)
    return kills


def test_run_timeout_kills_the_child_tree_and_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timeout kills the child's tree, then the child itself, and raises."""
    child = _FakeChild(hang=True)
    _install_popen(monkeypatch, child)
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    kills = _record_kills(monkeypatch)
    with pytest.raises(subprocess.TimeoutExpired):
        render._run(["tool"], 7)
    assert kills == [(child.pid, None)]
    assert child.killed
    assert child.waits == [7, 5]


def test_run_timeout_also_kills_the_recorded_word(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With a pid file of digits, the recorded Word is killed with the image filter."""
    _install_popen(monkeypatch, _FakeChild(hang=True))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    kills = _record_kills(monkeypatch)
    pid_file = tmp_path / "word.pid"
    pid_file.write_bytes(b"31337")
    with pytest.raises(subprocess.TimeoutExpired):
        render._run(["tool"], 7, pid_file=pid_file)
    assert kills == [(_FakeChild.pid, None), (31337, "WINWORD.EXE")]


@pytest.mark.parametrize(
    "content",
    [b"31337\n", b"abc", b"", b"-5", b"0", b"12345678901", b"9" * 40, b"1 2"],
)
def test_run_timeout_ignores_a_bad_pid_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: bytes
) -> None:
    """Anything but one to ten digits, a trailing newline included, is ignored."""
    _install_popen(monkeypatch, _FakeChild(hang=True))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    kills = _record_kills(monkeypatch)
    pid_file = tmp_path / "word.pid"
    pid_file.write_bytes(content)
    with pytest.raises(subprocess.TimeoutExpired):
        render._run(["tool"], 7, pid_file=pid_file)
    assert kills == [(_FakeChild.pid, None)]


def test_run_timeout_ignores_this_process_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pid file naming this process is never killed."""
    _install_popen(monkeypatch, _FakeChild(hang=True))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    kills = _record_kills(monkeypatch)
    pid_file = tmp_path / "word.pid"
    pid_file.write_bytes(str(os.getpid()).encode("ascii"))
    with pytest.raises(subprocess.TimeoutExpired):
        render._run(["tool"], 7, pid_file=pid_file)
    assert kills == [(_FakeChild.pid, None)]


def test_run_timeout_without_a_pid_file_kills_only_the_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing pid file is not an error."""
    _install_popen(monkeypatch, _FakeChild(hang=True))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    kills = _record_kills(monkeypatch)
    with pytest.raises(subprocess.TimeoutExpired):
        render._run(["tool"], 7, pid_file=tmp_path / "word.pid")
    assert kills == [(_FakeChild.pid, None)]


def test_docx_to_pdf_clears_a_stale_pid_file_and_leaves_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A `word.pid` from an earlier run is deleted before Word runs, and none is left after."""
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")
    pid_file = tmp_path / "word.pid"
    pid_file.write_bytes(b"31337")
    existed: list[bool] = []

    def fake_run(args: list[str], timeout: int, pid_file: Path | None = None) -> None:
        existed.append((tmp_path / "word.pid").exists())
        (tmp_path / "word.pid").write_bytes(b"555")
        (tmp_path / "word.pid.tmp").write_bytes(b"555")
        (tmp_path / "a.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr(render, "_run", fake_run)
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    render.docx_to_pdf(docx, tmp_path)
    assert existed == [False]
    assert not pid_file.exists()
    assert not (tmp_path / "word.pid.tmp").exists()


def test_docx_to_pdf_leaves_no_pid_file_when_the_step_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The pid files are removed on the failure path too."""
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")

    def fake_run(args: list[str], timeout: int, pid_file: Path | None = None) -> None:
        (tmp_path / "word.pid").write_bytes(b"555")
        (tmp_path / "word.pid.tmp").write_bytes(b"555")
        raise subprocess.TimeoutExpired("word", timeout)

    monkeypatch.setattr(render, "_run", fake_run)
    monkeypatch.setattr(render, "_soffice_path", lambda: None)
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    with pytest.raises(PdfConversionError, match="word: TimeoutExpired"):
        render.docx_to_pdf(docx, tmp_path)
    assert not (tmp_path / "word.pid").exists()
    assert not (tmp_path / "word.pid.tmp").exists()


def test_run_kills_the_converter_on_an_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl-C during the wait kills the converter's tree, then propagates."""
    child = _FakeChild()
    seen_waits: list[int | None] = []

    def interrupted(timeout: int | None = None) -> int:
        seen_waits.append(timeout)
        if len(seen_waits) == 1:
            raise KeyboardInterrupt
        return 0

    child.wait = interrupted  # type: ignore[method-assign]
    _install_popen(monkeypatch, child)
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    kills = _record_kills(monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        render._run(["tool"], 7)
    assert kills == [(child.pid, None)]
    assert child.killed


def test_run_interrupt_also_kills_the_recorded_word(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """On Windows a Ctrl-C kills the recorded Word too, as a timeout does."""
    child = _FakeChild()
    waits: list[int | None] = []

    def interrupted(timeout: int | None = None) -> int:
        waits.append(timeout)
        if len(waits) == 1:
            raise KeyboardInterrupt
        return 0

    child.wait = interrupted  # type: ignore[method-assign]
    _install_popen(monkeypatch, child)
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    kills = _record_kills(monkeypatch)
    pid_file = tmp_path / "word.pid"
    pid_file.write_bytes(b"31337")
    with pytest.raises(KeyboardInterrupt):
        render._run(["tool"], 7, pid_file=pid_file)
    assert kills == [(child.pid, None), (31337, "WINWORD.EXE")]
    assert child.killed


def _fake_system_root(tmp_path: Path) -> Path:
    root = tmp_path / "winroot"
    (root / "System32").mkdir(parents=True)
    (root / "System32" / "taskkill.exe").write_bytes(b"")
    return root


def test_kill_tree_runs_no_command_without_a_usable_systemroot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unset, relative or taskkill-less SYSTEMROOT runs nothing, with no PATH fallback."""
    ran: list[object] = []
    monkeypatch.setattr(render.subprocess, "run", lambda *a, **k: ran.append(a))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    monkeypatch.delenv("SYSTEMROOT", raising=False)
    render._kill_tree(99)
    monkeypatch.setenv("SYSTEMROOT", "")
    render._kill_tree(99)
    monkeypatch.setenv("SYSTEMROOT", "relative/root")
    render._kill_tree(99)
    monkeypatch.setenv("SYSTEMROOT", "\\\\host\\share\\Windows")
    render._kill_tree(99)
    monkeypatch.setenv("SYSTEMROOT", "//host/share/Windows")  # absolute on POSIX too
    render._kill_tree(99)
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "empty"))
    render._kill_tree(99)
    assert ran == []


def test_kill_tree_runs_the_system_taskkill(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """taskkill runs by its absolute path, with the tree flags and the optional image filter."""
    root = _fake_system_root(tmp_path)
    seen: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(render.subprocess, "run", lambda args, **k: seen.append((args, k)))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    monkeypatch.setenv("SYSTEMROOT", str(root))
    exe = str(root / "System32" / "taskkill.exe")
    render._kill_tree(99)
    render._kill_tree(100, image="WINWORD.EXE")
    assert seen[0][0] == [exe, "/PID", "99", "/T", "/F"]
    assert seen[1][0] == [exe, "/PID", "100", "/T", "/F", "/FI", "IMAGENAME eq WINWORD.EXE"]
    for _, kwargs in seen:
        assert kwargs["timeout"] == 10
        assert "shell" not in kwargs
        for stream in ("stdin", "stdout", "stderr"):
            assert kwargs[stream] is render.subprocess.DEVNULL


def test_kill_tree_suppresses_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A taskkill that fails or hangs never raises."""
    monkeypatch.setenv("SYSTEMROOT", str(_fake_system_root(tmp_path)))
    monkeypatch.setattr(render, "_ON_WINDOWS", True)

    def hang(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("taskkill", 10)

    monkeypatch.setattr(render.subprocess, "run", hang)
    render._kill_tree(99)


def test_kill_tree_on_posix_skips_unsafe_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """The process group of init, of nothing, or of this process is never killed."""
    killed: list[int] = []
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    monkeypatch.setattr(render.os, "killpg", lambda pid, sig: killed.append(pid), raising=False)
    monkeypatch.setattr(render.signal, "SIGKILL", 9, raising=False)
    for unsafe in (1, 0, -3, os.getpid()):
        render._kill_tree(unsafe)
    assert killed == []
    render._kill_tree(31337)
    assert killed == [31337]


@pytest.mark.skipif(sys.platform != "linux", reason="needs real POSIX process groups")
def test_a_timeout_kills_the_grandchild_too(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real child that starts a sleeping grandchild leaves nothing behind after a timeout."""
    monkeypatch.setattr(render, "subprocess", subprocess)
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    record = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, sys, time\n"
        "g = subprocess.Popen(['sleep', '60'])\n"
        "open(sys.argv[1], 'w').write(str(g.pid))\n"
        "time.sleep(60)\n"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        render._run([sys.executable, "-c", code, str(record)], 3)
    grandchild = int(record.read_text())

    def gone() -> bool:
        try:
            os.kill(grandchild, 0)
        except ProcessLookupError:
            return True
        try:
            stat = Path(f"/proc/{grandchild}/stat").read_text()
        except OSError:
            return True
        return stat.rsplit(")", 1)[1].split()[0] == "Z"

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not gone():
        time.sleep(0.1)
    assert gone()


def _page_count_setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, removable: bool) -> Path:
    kept = tmp_path / "ro-pagecount-test"

    def fake_mkdtemp(prefix: str = "") -> str:
        assert prefix == "ro-pagecount-"
        kept.mkdir()
        return str(kept)

    monkeypatch.setattr(render.tempfile, "mkdtemp", fake_mkdtemp)
    if not removable:
        monkeypatch.setattr(render.shutil, "rmtree", lambda *a, **k: None)
    monkeypatch.setattr(render, "docx_to_pdf", lambda copy, out_dir, timeout: out_dir / "a.pdf")
    monkeypatch.setattr(render, "count_pdf_pages", lambda p: 1)
    return _make_docx(tmp_path / "in.docx")


def test_page_count_warns_when_the_temp_copy_survives(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A temp folder that cannot be removed is reported in fixed text, with no path."""
    docx = _page_count_setup(monkeypatch, tmp_path, removable=False)
    with caplog.at_level(logging.WARNING, logger=render.__name__):
        assert render.page_count(docx) == 1
    records = [r for r in caplog.records if r.name == render.__name__]
    assert len(records) == 1
    assert not records[0].args
    assert records[0].getMessage() == (
        "A temporary copy of a document could not be removed. It is in the system temp folder, "
        "in a folder whose name starts with ro-pagecount-."
    )


def test_page_count_is_silent_when_the_temp_copy_is_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A normal run logs nothing and leaves no folder."""
    docx = _page_count_setup(monkeypatch, tmp_path, removable=True)
    with caplog.at_level(logging.WARNING, logger=render.__name__):
        assert render.page_count(docx) == 1
    assert [r for r in caplog.records if r.name == render.__name__] == []
    assert not (tmp_path / "ro-pagecount-test").exists()


def test_soffice_path_uses_the_exe_beside_a_com_launcher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """On Windows a PATH hit on `soffice.com` resolves to the sibling `soffice.exe`."""
    install = tmp_path / "outside" / "program"
    install.mkdir(parents=True)
    com = install / "soffice.com"
    exe = install / "soffice.exe"
    com.write_bytes(b"")
    exe.write_bytes(b"")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(render, "_SOFFICE_FALLBACKS", ())
    monkeypatch.setattr(render, "_ON_WINDOWS", True)
    monkeypatch.setattr(render.shutil, "which", lambda name: str(com))
    assert render._soffice_path() == str(exe.resolve())
    exe.unlink()
    assert render._soffice_path() is None


def test_soffice_path_off_windows_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Off Windows the PATH hit is used as found."""
    tool = tmp_path / "outside" / "soffice"
    tool.parent.mkdir()
    tool.write_bytes(b"")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(render, "_SOFFICE_FALLBACKS", ())
    monkeypatch.setattr(render, "_ON_WINDOWS", False)
    monkeypatch.setattr(render.shutil, "which", lambda name: str(tool))
    assert render._soffice_path() == str(tool.resolve())
