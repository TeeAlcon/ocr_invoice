from pathlib import Path
import re

import pandas as pd


INPUT_PATH = Path.cwd() / "outputs"
DOC_SEARCH_PATH = Path.cwd() / "outputs" / "doc_search_report.csv"
SLI_MAP_PATH = Path.cwd() / "outputs" / "sli_map.csv"


SEARCH_TERMS = (
    "SLI",
    "APL",
    "AVL",
    "Packing-List",
    "AWB",
    "SWB",
    "Other",
)

APL_AVL_SLI_FILENAME_RE = re.compile(
    r"^(apl|avl|sli).*?(\d+)\.pdf$",
    re.IGNORECASE,
)


def iter_folders(input_path: Path):
    return sorted(p for p in input_path.iterdir() if p.is_dir())


def iter_pdfs(folder: Path):
    return sorted(p for p in folder.rglob("*.pdf") if p.is_file())


def normalize_terms(search_terms):
    terms = list(search_terms)

    if not terms:
        raise ValueError("search_terms is required and cannot be empty")

    return [(term, term.lower()) for term in terms]


def parse_invoice_from_filename(pdf_path: Path):
    match = APL_AVL_SLI_FILENAME_RE.match(pdf_path.name)

    if not match:
        return None, None

    doc_type = match.group(1).upper()
    invoice_number = match.group(2).strip()

    return doc_type, invoice_number


def scan_folder(folder: Path, normalized_terms):
    summary_row = {
        "ITN": folder.name,
        "Total PDF count": 0,
        "Nonmatching count": 0,
        "Nonmatching filenames": "",
    }

    for term, _ in normalized_terms:
        summary_row[f"{term} file count"] = 0

    invoice_rows = []
    nonmatching_filenames = []
    seen_invoices = set()

    for pdf in iter_pdfs(folder):
        summary_row["Total PDF count"] += 1

        filename_lower = pdf.name.lower()
        matched_any = False

        for term, term_lower in normalized_terms:
            if term_lower in filename_lower:
                summary_row[f"{term} file count"] += 1
                matched_any = True

        if not matched_any:
            nonmatching_filenames.append(pdf.name)

        doc_type, invoice_number = parse_invoice_from_filename(pdf)

        if doc_type and invoice_number:
            invoice_key = (folder.name, doc_type, invoice_number)

            if invoice_key not in seen_invoices:
                seen_invoices.add(invoice_key)

                invoice_rows.append(
                    {
                        "ITN": folder.name,
                        "Invoice type": doc_type,
                        "Invoice number": invoice_number,
                    }
                )

    summary_row["Nonmatching count"] = len(nonmatching_filenames)
    summary_row["Nonmatching filenames"] = "; ".join(nonmatching_filenames)

    return summary_row, invoice_rows


def build_report_tables(input_path: Path, search_terms):
    normalized_terms = normalize_terms(search_terms)

    summary_rows = []
    invoice_rows = []

    for folder in iter_folders(input_path):
        folder_summary, folder_invoices = scan_folder(
            folder,
            normalized_terms,
        )

        summary_rows.append(folder_summary)
        invoice_rows.extend(folder_invoices)

    folder_summary_df = pd.DataFrame(summary_rows)
    folder_invoices_df = pd.DataFrame(invoice_rows)

    return folder_summary_df, folder_invoices_df


def export_doc_report(
    input_path: Path = INPUT_PATH,
    search_terms=SEARCH_TERMS,
    doc_report_path: Path = DOC_SEARCH_PATH,
    sli_map_path: Path = SLI_MAP_PATH,
):
    input_path = Path(input_path)
    doc_report_path = Path(doc_report_path)
    sli_map_path = Path(sli_map_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    doc_report_path.parent.mkdir(parents=True, exist_ok=True)

    folder_summary_df, folder_invoices_df = build_report_tables(
        input_path,
        search_terms,
    )

    folder_summary_df.to_csv(
        doc_report_path,
        index=False,
    )

    folder_invoices_df.to_csv(
        sli_map_path,
        index=False,
    )

    print(f"Results written to {doc_report_path}")
    print(f"Results written to {sli_map_path}")

    return {
        "folder_summary_df": folder_summary_df,
        "folder_invoices_df": folder_invoices_df,
        "doc_report_path": str(doc_report_path),
        "sli_map_path": str(sli_map_path),
    }


def main():
    export_doc_report()


if __name__ == "__main__":
    main()