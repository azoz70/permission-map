"""Parse bounded, single-sheet XLSX exports using the CSV validation pipeline."""

from io import BytesIO
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from defusedxml.common import DefusedXmlException
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from permission_map.importers.csv_importer import read_tabular_rows

MAX_ROWS = 50_000
MAX_COLUMNS = 64
MAX_EXPANDED_BYTES = 32 * 1024 * 1024


def _rows(sheet):
    # Ignore file-supplied worksheet dimensions and validate actual rows.
    sheet.reset_dimensions()
    width = None
    for number, row in enumerate(sheet.iter_rows(), start=1):
        if number > MAX_ROWS + 1 or len(row) > MAX_COLUMNS:
            raise ValueError("Excel worksheet exceeds row or column limit")
        if any(cell.data_type in {"f", "e"} for cell in row):
            raise ValueError("Excel formulas and error cells are unsupported")
        values = [str(cell.value) if cell.value is not None else "" for cell in row]
        while values and not values[-1]:
            values.pop()
        if width is None:
            width = len(values)
        elif values and len(values) <= width:
            values.extend([""] * (width - len(values)))
        yield values


def read_excel(data: bytes):
    try:
        with ZipFile(BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 128 or sum(item.file_size for item in members) > MAX_EXPANDED_BYTES:
                raise ValueError("Excel archive exceeds expanded size limit")
        workbook = load_workbook(BytesIO(data), read_only=True, keep_links=False)
        try:
            if len(workbook.sheetnames) != 1 or len(workbook.worksheets) != 1:
                raise ValueError("Excel import requires exactly one worksheet")
            return read_tabular_rows(iter(_rows(workbook.worksheets[0])))
        finally:
            workbook.close()
    except (
        BadZipFile,
        DefusedXmlException,
        InvalidFileException,
        KeyError,
        OSError,
        ParseError,
    ) as exc:
        raise ValueError("Invalid XLSX workbook") from exc
