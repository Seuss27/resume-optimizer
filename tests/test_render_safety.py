"""A3 render safety: active-content scan, converter command, environment, real page count."""

import importlib.util
import sys
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

    def fake_run(args: list[str], timeout: int) -> None:
        seen.append(args)
        (tmp_path / "a.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr(render, "_run", fake_run)
    render.docx_to_pdf(docx, tmp_path)
    assert seen[0][:3] == [sys.executable, "-I", "-c"]
    assert "from docx2pdf import convert" in seen[0][3]
    assert importlib.util.find_spec("docx2pdf") is not None

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


def test_run_passes_no_shell_a_timeout_a_scrubbed_env_and_no_pipes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real `_run` calls subprocess.run safely."""
    seen: dict[str, object] = {}

    def fake(args: list[str], **kwargs: object) -> None:
        seen.update(kwargs, args=args)

    monkeypatch.setattr(render.subprocess, "run", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    render._run(["tool", "arg"], 7)
    assert seen["args"] == ["tool", "arg"]
    assert seen["timeout"] == 7
    assert seen["check"] is True
    assert "shell" not in seen
    assert seen["stdout"] is render.subprocess.DEVNULL
    assert seen["stderr"] is render.subprocess.DEVNULL
    assert "GEMINI_API_KEY" not in seen["env"]  # type: ignore[operator]
