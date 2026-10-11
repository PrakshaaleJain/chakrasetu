"""Private, bounded document validation. No executable or macro-enabled uploads."""

from io import BytesIO
from pathlib import Path
import warnings
import zipfile
import re
from xml.etree import ElementTree as ET
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from PIL import Image, UnidentifiedImageError
from ..common import fail

MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 25 * 1024 * 1024
MAX_COUNT = 4
ALLOWED = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".txt"}


def validate_document(name, raw):
    suffix = Path(name).suffix.lower()
    if not raw or len(raw) > MAX_FILE:
        fail(
            "UPLOAD_SIZE_EXCEEDED",
            "Files must be nonempty and at most 10 MB.",
            status=422,
        )
    if suffix not in ALLOWED:
        fail(
            "UPLOAD_TYPE_UNSUPPORTED",
            "Use PDF, DOCX, XLSX, JPG, PNG or plain UTF-8 text.",
            status=422,
        )
    valid = False
    if suffix == ".pdf":
        if raw.startswith(b"%PDF-") and b"%%EOF" in raw[-2048:]:
            try:
                reader = PdfReader(BytesIO(raw), strict=True)
                valid = not reader.is_encrypted and len(reader.pages) <= 500

                # Inspect parsed keys too: PDF names may use escaped characters or object streams.
                def inert(obj, seen, depth=0):
                    if depth > 50:
                        return False
                    if hasattr(obj, "idnum"):
                        key = (obj.idnum, obj.generation)
                        if key in seen:
                            return True
                        seen.add(key)
                        obj = obj.get_object()
                    if isinstance(obj, dict):
                        return not any(
                            str(k)
                            in {
                                "/JavaScript",
                                "/JS",
                                "/Launch",
                                "/EmbeddedFile",
                                "/OpenAction",
                                "/AA",
                                "/RichMedia",
                                "/XFA",
                            }
                            for k in obj
                        ) and all(inert(v, seen, depth + 1) for v in obj.values())
                    if isinstance(obj, (list, tuple)):
                        return all(inert(v, seen, depth + 1) for v in obj)
                    return True

                valid = valid and inert(reader.trailer, set())
            except (
                PdfReadError,
                ValueError,
                KeyError,
                TypeError,
                RecursionError,
                OSError,
            ):
                valid = False
    elif suffix in [".jpg", ".jpeg", ".png"]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    valid = (
                        image.format == ("PNG" if suffix == ".png" else "JPEG")
                        and image.width * image.height <= 16000000
                    )
                    image.verify()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            valid = False
    elif suffix in [".docx", ".xlsx"]:
        try:
            with zipfile.ZipFile(BytesIO(raw)) as z:
                files = z.infolist()
                names = {f.filename for f in files}
                required = (
                    "word/document.xml" if suffix == ".docx" else "xl/workbook.xml"
                )
                valid = (
                    "[Content_Types].xml" in names
                    and required in names
                    and len(files) < 1000
                    and sum(f.file_size for f in files) <= 50 * 1024 * 1024
                )
                if valid:
                    for f in files:
                        if (
                            f.flag_bits & 1
                            or f.filename.startswith("/")
                            or ".." in Path(f.filename).parts
                            or any(
                                x in f.filename.lower()
                                for x in [
                                    "vbaproject",
                                    "embeddings/",
                                    "activex/",
                                    "externallinks/",
                                ]
                            )
                        ):
                            valid = False
                            break
                        if f.filename.endswith((".xml", ".rels")):
                            content = z.read(f)
                            decoded = content.decode("utf-8-sig")
                            if any(
                                x in decoded.lower()
                                for x in ["<!doctype", "<!entity", "macroenabled"]
                            ):
                                valid = False
                                break
                            root = ET.fromstring(decoded)
                            if any(
                                any(
                                    k.lower() == "targetmode"
                                    and v.lower() == "external"
                                    for k, v in node.attrib.items()
                                )
                                or (
                                    node.tag.rsplit("}", 1)[-1] in ["f", "instrText"]
                                    and re.search(
                                        r"(WEBSERVICE|HYPERLINK|DDE|INCLUDETEXT|INCLUDEPICTURE|\bEXEC\b|\bCALL\b|cmd\s*\|)",
                                        node.text or "",
                                        re.I,
                                    )
                                )
                                for node in root.iter()
                            ):
                                valid = False
                                break
        except (
            zipfile.BadZipFile,
            RuntimeError,
            OSError,
            KeyError,
            ET.ParseError,
            UnicodeDecodeError,
        ):
            valid = False
    else:
        try:
            valid = b"\0" not in raw and bool(raw.decode("utf-8"))
        except UnicodeDecodeError:
            valid = False
    if not valid:
        fail(
            "UPLOAD_CONTENT_INVALID",
            "File content is invalid, unsafe, active, encrypted, or does not match its permitted format.",
            status=422,
        )
