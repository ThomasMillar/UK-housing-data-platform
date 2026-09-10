import os
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


DATA_PAGE = "https://www.gov.uk/government/statistical-data-sets/price-paid-data-yearly-file"

# Resolve project root from scripts/download_monthly_data.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

START_YEAR = int(os.getenv("START_YEAR", "2019"))
END_YEAR = int(os.getenv("END_YEAR", "2025"))

# Matches pp-2024.csv or pp-2024-part1.csv
FILE_PATTERN = re.compile(r"pp-(\d{4})(?:-part(\d+))?\.csv$", re.IGNORECASE)


if START_YEAR > END_YEAR:
    raise ValueError(
        f"START_YEAR ({START_YEAR}) cannot be greater than END_YEAR ({END_YEAR})."
    )


def get_yearly_links():
    """Find the required HM Land Registry yearly CSV files."""

    print(f"Looking for Price Paid Data from {START_YEAR} to {END_YEAR}...")

    try:
        response = requests.get(DATA_PAGE, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Unable to access HM Land Registry download page: {exc}"
        ) from exc

    soup = BeautifulSoup(response.text, "html.parser")
    files_by_year = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        filename = urlparse(href).path.split("/")[-1]
        match = FILE_PATTERN.search(filename)

        if not match:
            continue

        year = int(match.group(1))

        if not START_YEAR <= year <= END_YEAR:
            continue

        part_number = match.group(2)

        files_by_year.setdefault(year, []).append({
            "year": year,
            "part": int(part_number) if part_number else None,
            "filename": filename,
            "url": urljoin(DATA_PAGE, href),
        })

    selected_files = []

    for year in range(START_YEAR, END_YEAR + 1):
        available = files_by_year.get(year, [])

        if not available:
            print(f"WARNING: No yearly CSV found for {year}")
            continue

        part_files = [file for file in available if file["part"] is not None]
        complete_files = [file for file in available if file["part"] is None]

        # Prefer split files when Land Registry provides them.
        if part_files:
            part_files.sort(key=lambda file: file["part"])
            print(f"{year}: using {len(part_files)} part files")
            selected_files.extend(part_files)

        elif complete_files:
            complete_files.sort(key=lambda file: file["filename"])
            selected = complete_files[0]

            print(f"{year}: using complete yearly file {selected['filename']}")
            selected_files.append(selected)

    return selected_files


def download_file(file_info):
    """Download a CSV only when it is not already stored locally."""

    filename = file_info["filename"]
    filepath = os.path.join(RAW_DIR, filename)

    if os.path.exists(filepath):
        print(f"Already downloaded: {filename}")
        return

    print(f"Downloading: {filename}")

    try:
        response = requests.get(file_info["url"], timeout=300, stream=True)
        response.raise_for_status()

        os.makedirs(RAW_DIR, exist_ok=True)

        # Stream in 1 MB chunks so large yearly files are not held in memory.
        with open(filepath, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output_file.write(chunk)

        print(f"Saved: {filename}")

    except requests.exceptions.RequestException as exc:
        print(f"ERROR downloading {filename}: {exc}")


if __name__ == "__main__":
    files = get_yearly_links()

    print(f"\nSelected {len(files)} CSV files for {START_YEAR}-{END_YEAR}.\n")

    for file_info in files:
        download_file(file_info)

    print("\nDownload stage complete.")