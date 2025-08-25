from docx import Document
from typing import Dict


def replace_placeholders_in_docx_bytes(docx_bytes: bytes, variables: Dict[str, str]) -> bytes:
    """Replace {{placeholders}} in a DOCX (bytes) and return modified bytes.
    Note: This performs a simple run-level replacement. Placeholders split across runs may not be replaced.
    """
    from io import BytesIO

    input_buffer = BytesIO(docx_bytes)
    document = Document(input_buffer)

    def replace_in_paragraph(paragraph):
        for run in paragraph.runs:
            if run.text:
                new_text = run.text
                for key, value in variables.items():
                    placeholder = f"{{{{{key}}}}}"
                    new_text = new_text.replace(placeholder, str(value))
                run.text = new_text

    def replace_in_table(table):
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_in_paragraph(p)

    for paragraph in document.paragraphs:
        replace_in_paragraph(paragraph)

    for table in document.tables:
        replace_in_table(table)

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output.getvalue()


