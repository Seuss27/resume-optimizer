"""Real page counts for generated Word documents (plan §3.9, task A3).

A `.docx` is converted to PDF by Word or, failing that, by `soffice --headless`, and `pypdf`
counts the pages (plan §3.9 says which converter runs where). If neither converter works this fails
loudly. It never estimates a count.

The document is built from model output, so before any converter opens it, it is scanned for
active content (fields, embedded objects, external targets; plan §3.7). A document that has any
is refused, not opened.
"""

import contextlib
import os
import re
import shutil
import signal
import subprocess  # noqa: S404 - fixed argument lists only, never a shell
import sys
import tempfile
import zipfile
from pathlib import Path

from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)

CONVERT_TIMEOUT_SECONDS: int = 120

# A module flag, so tests can patch it without patching `os.name`.
_ON_WINDOWS: bool = os.name == "nt"

_PID_FILE_NAME: str = "word.pid"

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


_TEMP_LEFT_WARNING: str = (
    "A temporary copy of a document could not be removed. It is in the system temp folder, "
    "in a folder whose name starts with ro-pagecount-."
)


class PdfConversionError(RuntimeError):
    """No converter could turn the document into a PDF, or the document was refused."""


class DocumentRefusedError(PdfConversionError):
    """The document has active content, or could not be scanned, so it must not be used."""


def _converter_env() -> dict[str, str]:
    """A minimal environment for a converter: no credentials."""
    return {k: v for k, v in os.environ.items() if k.upper() in _ENV_ALLOWLIST}


def _kill_tree(pid: int, image: str | None = None) -> None:
    """Kills a process and everything it started. Every failure is suppressed.

    On Windows this runs `taskkill` from `SYSTEMROOT` only (never a PATH lookup), and `image`
    limits the kill to processes of that image name. On POSIX it kills the process group.
    """
    if _ON_WINDOWS:
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            root: str = os.environ.get("SYSTEMROOT", "")
            if not root or not Path(root).is_absolute() or root.startswith(("\\\\", "//")):
                return  # unset, relative or a network share: never run a binary from there
            taskkill: Path = Path(root) / "System32" / "taskkill.exe"
            if not taskkill.exists():
                return
            args: list[str] = [str(taskkill), "/PID", str(pid), "/T", "/F"]
            if image:
                args += ["/FI", f"IMAGENAME eq {image}"]
            subprocess.run(  # noqa: S603 - fixed list, an absolute system path, no shell
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=_converter_env(),
                timeout=10,
            )
        return
    if pid <= 1 or pid == os.getpid():
        return
    with contextlib.suppress(OSError):
        os.killpg(pid, signal.SIGKILL)


def _recorded_word_pid(pid_file: Path) -> int | None:
    """Reads the Word id the converter recorded, only if it is plain digits and plausible."""
    data: bytes = b""
    with contextlib.suppress(OSError), pid_file.open("rb") as handle:
        data = handle.read(16)
    if not re.fullmatch(rb"[0-9]{1,10}", data):
        return None
    pid: int = int(data)
    return pid if pid > 0 and pid != os.getpid() else None


def _run(args: list[str], timeout: int, pid_file: Path | None = None) -> None:
    """Runs one converter command, raising on failure or timeout.

    On a timeout or any other abort (Ctrl-C included) the converter's whole process tree is
    killed, and so is the Word this run started, when the converter recorded its id in
    `pid_file`.
    """
    options: dict[str, bool] = {} if _ON_WINDOWS else {"start_new_session": True}
    child = subprocess.Popen(  # noqa: S603 - arguments are a fixed list built from local paths
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_converter_env(),
        **options,
    )
    try:
        child.wait(timeout=timeout)
    except BaseException:
        # A timeout, Ctrl-C or any other abort. On POSIX the converter has its own session, so
        # the terminal's interrupt never reaches it. Do not leave it, or its Word, running.
        _kill_tree(child.pid)
        if _ON_WINDOWS and pid_file is not None:
            word_pid: int | None = _recorded_word_pid(pid_file)
            if word_pid is not None:
                _kill_tree(word_pid, image="WINWORD.EXE")
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            child.kill()
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            child.wait(timeout=5)
        raise
    if child.returncode != 0:
        raise subprocess.CalledProcessError(child.returncode, args)


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
    candidate: Path = Path(found)
    swapped: bool = _ON_WINDOWS and candidate.suffix.lower() == ".com"
    if swapped:
        # PATH resolves `soffice` to the `.com` launcher. Use the `.exe` beside it.
        candidate = candidate.with_name("soffice.exe")
    resolved: Path = candidate.resolve()
    if resolved.is_relative_to(Path.cwd().resolve()):
        return None
    if _ON_WINDOWS and resolved.suffix.lower() != ".exe":
        return None
    if swapped and not resolved.is_file():
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

    pid_file: Path = target_dir / _PID_FILE_NAME
    pid_files: tuple[Path, Path] = (pid_file, pid_file.with_name(f"{_PID_FILE_NAME}.tmp"))
    if _ON_WINDOWS:
        label: str = "word"
        word_args: list[str] = [
            sys.executable, "-I", "-m", "resume_optimizer.word_pdf",
            str(source), str(pdf_path), str(pid_file),
        ]  # fmt: skip
    else:
        label = "docx2pdf"
        word_args = [sys.executable, "-I", "-c", _DOCX2PDF_SNIPPET, str(source), str(pdf_path)]
    try:
        if _ON_WINDOWS:
            # A stale id from an earlier run must never be killed.
            for stale in pid_files:
                stale.unlink(missing_ok=True)
            _run(word_args, timeout, pid_file=pid_file)
        else:
            _run(word_args, timeout)
        if pdf_path.exists():
            return pdf_path
        failures.append(f"{label} produced no file")
    except (OSError, subprocess.SubprocessError) as exc:
        failures.append(f"{label}: {type(exc).__name__}")
    finally:
        if _ON_WINDOWS:
            for leftover in pid_files:
                with contextlib.suppress(OSError):
                    leftover.unlink(missing_ok=True)

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
    tmp: str = tempfile.mkdtemp(prefix="ro-pagecount-")
    try:
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if Path(tmp).exists():
            # Fixed text: no path, no document name (CLAUDE.md rule 4).
            logger.warning(_TEMP_LEFT_WARNING)
