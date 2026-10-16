"""xlsx bytes of an openpyxl workbook with no author and no generating application
in the document properties."""
import io
import zipfile

_APP_PART = "docProps/app.xml"
_EMPTY_APP = ('<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
              'extended-properties"/>')


def workbook_bytes(wb):
    """The workbook as xlsx bytes, without creator, lastModifiedBy or application."""
    wb.properties.creator = None
    wb.properties.lastModifiedBy = None
    buffer = io.BytesIO()
    wb.save(buffer)
    return _without_application(buffer.getvalue())


def _without_application(content):
    """The xlsx with empty extended properties, so it names no generating application."""
    source = zipfile.ZipFile(io.BytesIO(content))
    buffer = io.BytesIO()
    with source, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = _EMPTY_APP.encode() if item.filename == _APP_PART else source.read(item)
            target.writestr(item, data)
    return buffer.getvalue()
