import sys

import fitz  # PyMuPDF


def combine_pdfs(output_path, *input_paths):
    """
    Combine multiple PDFs into a single PDF.

    Parameters:
    output_path (str): The path to save the combined PDF.
    input_paths (str): Paths of the PDF files to be combined.

    Returns:
    None
    """
    # Create a new PDF document
    combined_pdf = fitz.open()

    for pdf_path in input_paths:
        # Open the current PDF
        pdf_document = fitz.open(pdf_path)
        
        # Iterate through each page in the current PDF
        for page_num in range(pdf_document.page_count):
            # Get the current page
            page = pdf_document.load_page(page_num)
            # Add the page to the combined PDF
            combined_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)

    # Save the combined PDF to the output path
    combined_pdf.save(output_path)


if __name__ == "__main__":

    # first parameter is the output file name from the cli
    out_name = sys.argv[1]

    # the rest of the parameters are the input files from the cli
    in_names = sys.argv[2:]

    # Example usage:
    combine_pdfs(out_name, *in_names)