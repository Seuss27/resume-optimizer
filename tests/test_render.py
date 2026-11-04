"""Tests for the page-count helpers (plan task A3). No Word, LibreOffice or real PDF needed."""

import zipfile
from pathlib import Path

import pytest

from resume_optimizer import render
from resume_optimizer.render import PdfConversionError


def test_docx_to_pdf_falls_back_to_soffice(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When docx2pdf fails, soffice is used."""
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")
    calls: list[str] = []

    def fake_run(args: list[str], timeout: int) -> None:
        calls.append(args[0])
        if any("docx2pdf" in a for a in args):
            raise OSError("no word")
        (tmp_path / "a.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr(render, "_run", fake_run)
    monkeypatch.setattr(render, "_soffice_path", lambda: "soffice")
    assert render.docx_to_pdf(docx, tmp_path) == (tmp_path / "a.pdf").resolve()
    assert len(calls) == 2


def test_docx_to_pdf_fails_loudly_without_converters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no working converter the error is raised, never an estimate."""
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")

    def fake_run(args: list[str], timeout: int) -> None:
        raise OSError("nope")

    monkeypatch.setattr(render, "_run", fake_run)
    monkeypatch.setattr(render, "_soffice_path", lambda: None)
    with pytest.raises(PdfConversionError):
        render.docx_to_pdf(docx, tmp_path)


def test_page_count_missing_document(tmp_path: Path) -> None:
    """A missing document raises the conversion error."""
    with pytest.raises(PdfConversionError):
        render.page_count(tmp_path / "missing.docx")


def test_page_count_uses_pdf_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The count comes from the converted PDF."""
    docx = tmp_path / "a.docx"
    with zipfile.ZipFile(docx, "w") as package:
        package.writestr("word/document.xml", "<w:document/>")

    def fake_convert(docx_path: Path, out_dir: Path, timeout: int) -> Path:
        pdf = out_dir / "a.pdf"
        pdf.write_bytes(b"%PDF")
        return pdf

    monkeypatch.setattr(render, "docx_to_pdf", fake_convert)
    monkeypatch.setattr(render, "count_pdf_pages", lambda p: 2)
    assert render.page_count(docx) == 2
