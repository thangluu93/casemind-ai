"""Bounded PDF parsing in an isolated, disposable process."""
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import threading
import zlib

from .models import SourceObjectRef

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_PAGES = 50
MAX_PIXELS = 16_000_000
MAX_DECOMPRESSED_BYTES = 128 * 1024 * 1024


def _chunk(kind, data):
    return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)


def _render(pdf):
    import resource
    import pypdfium2 as pdfium
    if pdfium.PDFIUM_INFO.flags:
        raise ValueError("Active PDFium build is prohibited")
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    document = pdfium.PdfDocument(pdf)
    try:
        if not 1 <= len(document) <= MAX_PAGES:
            raise ValueError("PDF page allowance exceeded")
        pages, total = [], 0
        for index in range(len(document)):
            page = document[index]
            try:
                width, height = page.get_size()
                if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                    raise ValueError("Invalid page dimensions")
                pixels = math.ceil(width) * math.ceil(height)
                total += pixels * 4
                if pixels > MAX_PIXELS or total > MAX_DECOMPRESSED_BYTES:
                    raise ValueError("PDF pixel allowance exceeded")
                bitmap = page.render(scale=1, rev_byteorder=True, prefer_bgrx=False)
                try:
                    if bitmap.format != pdfium.raw.FPDFBitmap_BGR:
                        raise ValueError("Unsupported raster format")
                    data = bytes(bitmap.buffer)
                    rows = b"".join(b"\0" + data[y * bitmap.stride:y * bitmap.stride + bitmap.width * 3] for y in range(bitmap.height))
                    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack("!IIBBBBB", bitmap.width, bitmap.height, 8, 2, 0, 0, 0))
                    png += _chunk(b"IDAT", zlib.compress(rows)) + _chunk(b"IEND", b"")
                    pages.append(base64.b64encode(png).decode())
                finally:
                    bitmap.close()
            finally:
                page.close()
        return pages
    finally:
        document.close()


def render_document(pdf: bytes, original_ref: SourceObjectRef | dict) -> list[dict]:
    ref = SourceObjectRef.model_validate(original_ref)
    if (not pdf.startswith(b"%PDF-") or len(pdf) > MAX_INPUT_BYTES or len(pdf) != ref.byte_size or hashlib.sha256(pdf).hexdigest() != ref.sha256 or ref.media_type != "application/pdf"):
        raise ValueError("Invalid PDF original")
    try:
        process = subprocess.Popen([sys.executable, "-m", "casemind.document_rendering"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        finished = threading.Event()
        exceeded = []
        def monitor():
            while not finished.wait(0.05):
                try:
                    if sys.platform.startswith("linux"):
                        status = Path(f"/proc/{process.pid}/status").read_text()
                        rss = next((line.split()[1] for line in status.splitlines() if line.startswith("VmRSS:")), "0")
                    else:
                        rss = subprocess.check_output(["ps", "-o", "rss=", "-p", str(process.pid)], timeout=1).strip() or b"0"
                    if int(rss) > 512 * 1024:
                        exceeded.append(True)
                        process.kill()
                        return
                except (subprocess.SubprocessError, ValueError, OSError):
                    if process.poll() is not None:
                        return
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        try:
            output, error = process.communicate(pdf, timeout=15)
            if process.returncode or exceeded:
                raise ValueError("PDF parser resource or format failure")
            pages = json.loads(output)
        finally:
            finished.set()
            if process.poll() is None:
                process.kill()
                process.communicate()
            thread.join(timeout=2)
    except (subprocess.SubprocessError, ValueError) as exc:
        raise ValueError("PDF preflight or rendering failed") from exc
    return [{"page": i + 1, "bytes": base64.b64decode(data), "sha256": hashlib.sha256(base64.b64decode(data)).hexdigest(), "media_type": "image/png", "original_sha256": ref.sha256, "original_generation": ref.generation, "renderer": "pypdfium2-5.0.0"} for i, data in enumerate(pages)]


if __name__ == "__main__":
    print(json.dumps(_render(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))))
