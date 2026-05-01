from openpyxl.styles import Font


EXPORT_MAX_ROWS = 10_000
UTF8_BOM = "\ufeff"


def style_header_row(sheet):
    for cell in sheet[1]:
        cell.font = Font(bold=True)


def auto_fit_columns(sheet, max_width: int):
    for column_cells in sheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = str(cell.value) if cell.value is not None else ""
            if len(value) > max_length:
                max_length = len(value)
        sheet.column_dimensions[column_letter].width = min(max_length + 2, max_width)
