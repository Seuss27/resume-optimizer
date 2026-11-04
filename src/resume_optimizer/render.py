"""Real page counts for generated Word documents (plan §3.9, task A3).

A `.docx` is converted to PDF by Word (through `docx2pdf`) or, failing that, by
`soffice --headless`, and `pypdf` counts the pages. If neither converter works this fails
loudly. It never estimates a count.

The document is built from model output, so before any converter opens it, it is scanned for
active content (fields, embedded objects, external targets; plan §3.7). A document that has any
is refused, not opened.
"""

import os
import re
import shutil
import subprocess  # noqa: S404 - fixed argument lists only, never a shell
import sys
import tempfile
import zipfile
from pathlib import Path

from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)

CONVERT_TIMEOUT_SECONDS: int = 120

# Environment variables a converter needs. Everything else, API keys included, is withheld.
_ENV_ALLOWLIST: tuple[str, ...] = (
    "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "USERPROFILE", "APPDATA",
    "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "HOME", "USER",
    "USERNAME", "COMPUTERNAME", "DISPLAY", "LANG", "LC_ALL",
)  # fmt: skip

# Markers of active content in a document part, matched as element openings.
_ACTIVE_MARKERS: tuple[tuple[str, str], ...] = (
    ("<w:fldSimple", "field"),
    ("<w:fldChar", "field"),
    ("<w:instrText", "field"),
    ("<w:delInstrText", "field"),
    ("<w:altChunk", "embedded chunk"),
    ("<w:object", "embedded object"),
    ("<w:control", "control"),
)

# A relationship element (quoted attribute values may contain ">"), and its attributes.
_RELATIONSHIP = re.compile(r"<Relationship\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>", re.IGNORECASE)
_ATTRIBUTE = re.compile(r"([A-Za-z:]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")

# Hyperlinks (the contact line) are expected, but only to these destinations.
_ALLOWED_LINK_PREFIXES: tuple[str, ...] = ("https://", "mailto:")

# A resume built by pandoc has no images, so any media part is suspect. Zip-bomb guard too.
_MAX_UNCOMPRESSED_BYTES: int = 50 * 1024 * 1024

_DOCX2PDF_SNIPPET: str = (
    "import sys; from docx2pdf import convert; convert(sys.argv[1], sys.argv[2])"
)

_SOFFICE_FALLBACKS: tuple[str, ...] = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


class PdfConversionError(RuntimeError):
    """No converter could turn the document into a PDF, or the document was refused."""


class DocumentRefusedError(PdfConversionError):
    """The document has active content, or could not be scanned, so it must not be used."""


def _converter_env() -> dict[str, str]:
    """A minimal environment for a converter: no credentials."""
    return {k: v for k, v in os.environ.items() if k.upper() in _ENV_ALLOWLIST}


def _run(args: list[str], timeout: int) -> None:
    """Runs one converter command, raising on failure or timeout."""
    subprocess.run(  # noqa: S603 - arguments are a fixed list built from local paths
        args,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        env=_converter_env(),
    )


def _relationship_kinds(part_text: str) -> set[str]:
    """Flags external relationships other than allowed hyperlinks."""
    kinds: set[str] = set()
    for rel in _RELATIONSHIP.findall(part_text):
        attrs: dict[str, str] = {
            m.group(1).lower(): m.group(2) if m.group(2) is not None else m.group(3)
            for m in _ATTRIBUTE.finditer(rel)
        }
        if attrs.get("targetmode", "").lower() != "external":
            continue
        is_link: bool = attrs.get("type", "").lower().endswith("/hyperlink")
        if not (is_link and attrs.get("target", "").lower().startswith(_ALLOWED_LINK_PREFIXES)):
            kinds.add("external target")
    return kinds


def scan_for_active_content(docx_path: Path) -> list[str]:
    """Lists the kinds of active content found in a `.docx`, without opening it in Word.

    Returns:
        Sorted, de-duplicated kind names (never document text). Empty when the document is clean.

    Raises:
        PdfConversionError: If the file is not a readable, ordinary zip package.
    """
    kinds: set[str] = set()
    try:
        with zipfile.ZipFile(docx_path) as package:
            infos: list[zipfile.ZipInfo] = package.infolist()
            names: list[str] = [i.filename.lower() for i in infos]
            if len(set(names)) != len(names):
                raise DocumentRefusedError("refused: duplicate parts in the package")
            if sum(i.file_size for i in infos) > _MAX_UNCOMPRESSED_BYTES:
                raise DocumentRefusedError("refused: package is too large")
            for info in infos:
                name: str = info.filename.lower()
                if name.startswith("word/media/") or "/embeddings/" in name:
                    kinds.add("embedded media")
                    continue
                if name.endswith((".bin", ".ole")):
                    kinds.add("embedded object")
                    continue
                if not name.endswith((".xml", ".rels")):
                    continue
                text: str = package.read(info).decode("utf-8", errors="replace")
                kinds.update(kind for marker, kind in _ACTIVE_MARKERS if marker in text)
                kinds.update(_relationship_kinds(text))
    except DocumentRefusedError:
        raise
    except Exception as exc:  # noqa: BLE001 - any parse failure is a refusal, never a crash
        raise DocumentRefusedError(f"refused: not a readable .docx ({type(exc).__name__})") from exc
    return sorted(kinds)


def _soffice_path() -> str | None:
    """Finds LibreOffice in its usual install folders, then on PATH (never in the working dir)."""
    known: str | None = next((p for p in _SOFFICE_FALLBACKS if Path(p).exists()), None)
    if known:
        return known
    found: str | None = shutil.which("soffice")
    if not found:
        return None
    resolved: Path = Path(found).resolve()
    if resolved.is_relative_to(Path.cwd().resolve()):
        return None
    if os.name == "nt" and resolved.suffix.lower() != ".exe":
        return None
    return str(resolved)


def docx_to_pdf(docx_path: Path, out_dir: Path, timeout: int = CONVERT_TIMEOUT_SECONDS) -> Path:
    """Converts a `.docx` to PDF in `out_dir`.

    Args:
        docx_path: The document to convert.
        out_dir: An existing directory that receives the PDF.
        timeout: Seconds each converter may run.

    Returns:
        The path of the PDF.

    Raises:
        PdfConversionError: If neither Word nor LibreOffice produced the PDF.
    """
    source: Path = docx_path.resolve()
    target_dir: Path = out_dir.resolve()
    pdf_path: Path = target_dir / f"{source.stem}.pdf"
    failures: list[str] = []

    try:
        _run([sys.executable, "-I", "-c", _DOCX2PDF_SNIPPET, str(source), str(pdf_path)], timeout)
        if pdf_path.exists():
            return pdf_path
        failures.append("docx2pdf produced no file")
    except (OSError, subprocess.SubprocessError) as exc:
        failures.append(f"docx2pdf: {type(exc).__name__}")

    soffice: str | None = _soffice_path()
    if soffice:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            try:
                _run(
                    [soffice, f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
                     "--headless", "--convert-to", "pdf", "--outdir", str(target_dir),
                     str(source)],
                    timeout,
                )  # fmt: skip
                if pdf_path.exists():
                    return pdf_path
                failures.append("soffice produced no file")
            except (OSError, subprocess.SubprocessError) as exc:
                failures.append(f"soffice: {type(exc).__name__}")
    else:
        failures.append("soffice not installed")

    raise PdfConversionError("; ".join(failures))


def count_pdf_pages(pdf_path: Path) -> int:
    """Counts the pages of a PDF with pypdf.

    Raises:
        PdfConversionError: If the PDF cannot be read.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfConversionError("pypdf is not installed") from exc

    try:
        return len(PdfReader(str(pdf_path)).pages)
    except Exception as exc:  # noqa: BLE001 - any parse failure is a conversion error
        raise PdfConversionError(f"PDF unreadable ({type(exc).__name__})") from exc


def page_count(docx_path: Path, timeout: int = CONVERT_TIMEOUT_SECONDS) -> int:
    """Returns the real page count of a `.docx`, via a throwaway PDF.

    Raises:
        PdfConversionError: If the document was refused or could not be converted or read.
    """
    if not docx_path.exists():
        raise PdfConversionError("document not found")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # Scan and convert one private copy, so the file that was checked is the file opened,
        # and no lock file or recent-files entry carries the real name.
        copy: Path = Path(tmp) / "document.docx"
        try:
            shutil.copyfile(docx_path, copy)
        except OSError as exc:
            raise DocumentRefusedError(
                f"refused: could not copy document ({type(exc).__name__})"
            ) from exc
        active: list[str] = scan_for_active_content(copy)
        if active:
            raise DocumentRefusedError(f"refused: document contains {', '.join(active)}")
        pdf_path: Path = docx_to_pdf(copy, Path(tmp), timeout)
        return count_pdf_pages(pdf_path)
