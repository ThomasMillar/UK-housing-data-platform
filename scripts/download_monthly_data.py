import os
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# CONFIGURATION

DATA_PAGE = (
    "https://www.gov.uk/government/"
    "statistical-data-sets/price-paid-data-yearly-file"
)

# Resolve the project root from this script's location.
# scripts/download_monthly_data.py -> project root -> data/raw
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RAW_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
)

START_YEAR = int(
    os.getenv("START_YEAR", "2019")
)

END_YEAR = int(
    os.getenv("END_YEAR", "2025")
)


FILE_PATTERN = re.compile(
    r"pp-(\d{4})(?:-part(\d+))?\.csv$",
    re.IGNORECASE,
)


# VALIDATE CONFIGURATION

if START_YEAR > END_YEAR:
    raise ValueError(
        f"START_YEAR ({START_YEAR}) cannot be greater "
        f"than END_YEAR ({END_YEAR})."
    )


# DISCOVER AVAILABLE FILES

def get_yearly_links():
    """
    Discover HM Land Registry yearly CSV files.

    Where part files are available, prefer those over the
    complete yearly CSV.

    Example:

        2021 -> part1 + part2
        2024 -> complete yearly file
    """

    print(
        f"Looking for Price Paid Data from "
        f"{START_YEAR} to {END_YEAR}..."
    )

    try:
        response = requests.get(
            DATA_PAGE,
            timeout=30,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as exc:

        raise RuntimeError(
            f"Unable to access HM Land Registry download page: "
            f"{exc}"
        )


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )


    files_by_year = {}


    for link in soup.find_all(
        "a",
        href=True,
    ):

        href = link["href"]

        filename = (
            urlparse(href)
            .path
            .split("/")[-1]
        )


        match = FILE_PATTERN.search(
            filename
        )

        if not match:
            continue


        year = int(
            match.group(1)
        )


        if year < START_YEAR or year > END_YEAR:
            continue


        part_number = match.group(2)

        full_url = urljoin(
            DATA_PAGE,
            href,
        )


        files_by_year.setdefault(
            year,
            [],
        ).append(
            {
                "year": year,
                "part": (
                    int(part_number)
                    if part_number
                    else None
                ),
                "filename": filename,
                "url": full_url,
            }
        )


    selected_files = []


    for year in range(
        START_YEAR,
        END_YEAR + 1,
    ):

        available = files_by_year.get(
            year,
            [],
        )


        if not available:

            print(
                f"WARNING: No yearly CSV found for {year}"
            )

            continue


        part_files = [
            item
            for item in available
            if item["part"] is not None
        ]


        complete_files = [
            item
            for item in available
            if item["part"] is None
        ]


        if part_files:

            part_files.sort(
                key=lambda item: item["part"]
            )

            print(
                f"{year}: using "
                f"{len(part_files)} part files"
            )

            selected_files.extend(
                part_files
            )

        elif complete_files:

            complete_files.sort(
                key=lambda item: item["filename"]
            )

            selected = complete_files[0]

            print(
                f"{year}: using complete yearly file "
                f"{selected['filename']}"
            )

            selected_files.append(
                selected
            )


    return selected_files


# DOWNLOAD

def download_file(file_info):
    """
    Download a single CSV file if it does not
    already exist locally.
    """

    filename = file_info["filename"]

    filepath = os.path.join(
        RAW_DIR,
        filename,
    )


    if os.path.exists(filepath):

        print(
            f"Already downloaded: {filename}"
        )

        return


    print(
        f"Downloading: {filename}"
    )


    try:

        response = requests.get(
            file_info["url"],
            timeout=300,
            stream=True,
        )

        response.raise_for_status()


        os.makedirs(
            RAW_DIR,
            exist_ok=True,
        )


        with open(
            filepath,
            "wb",
        ) as output_file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:

                    output_file.write(
                        chunk
                    )


        print(
            f"Saved: {filename}"
        )


    except requests.exceptions.RequestException as exc:

        print(
            f"ERROR downloading "
            f"{filename}: {exc}"
        )


# MAIN

if __name__ == "__main__":

    files = get_yearly_links()


    print(
        f"\nSelected {len(files)} CSV files "
        f"for {START_YEAR}-{END_YEAR}.\n"
    )


    for file_info in files:

        download_file(
            file_info
        )


    print(
        "\nDownload stage complete."
    )