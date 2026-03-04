from flask import make_response
from werkzeug import Response


def _clean_filename(filename: str | None, extension: str) -> str:
    """Ensures filename has the correct extension, defaulting to 'unknown' if None."""
    filename = filename or "unknown"
    if not filename.endswith(f".{extension}"):
        filename = f"{filename}.{extension}"
    return filename


def download_file(data: bytes, filename: str, mimetype: str) -> Response:
    """Creates a file download response with the specified data, filename, and MIME type."""
    response = make_response(data)
    response.headers.set("Content-Type", mimetype)
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response


def download_pdf(data: bytes, filename: str | None) -> Response:
    """Creates a PDF (.pdf) download response."""
    filename = _clean_filename(filename, "pdf")
    mimetype = "application/pdf"
    return download_file(data, filename, mimetype)


def download_xlsx(data: bytes, filename: str | None) -> Response:
    """Creates an Excel (.xlsx) download response."""
    filename = _clean_filename(filename, "xlsx")
    mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return download_file(data, filename, mimetype)
