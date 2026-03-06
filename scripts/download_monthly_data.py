import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Config

PAGES = [
    "https://www.data.gov.uk/dataset/314f77b3-e702-4545-8bcb-9ef8262ea0fd/archived-price-paid-information-residential-property-1995-2017",
    "https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads"
]

RAW_DIR = os.path.join("..", "data", "raw")

# Only download part 1/2 files
PART_PATTERN = re.compile(r"pp-(\d{4})-part\d+\.csv$", re.IGNORECASE)


# Links

def get_part_links():
    all_links = set()

    for page in PAGES:
        print(f"Fetching page: {page}")

        try:
            response = requests.get(page, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            filename = href.split("/")[-1]

            if PART_PATTERN.search(filename):
                full_url = urljoin(page, href)
                all_links.add(full_url)

    return sorted(all_links)


# Download Files

def download_file(url):
    filename = url.split("/")[-1]
    filepath = os.path.join(RAW_DIR, filename)

    if os.path.exists(filepath):
        print(f"Already downloaded: {filename}")
        return

    print(f"Downloading: {filename}")

    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            os.makedirs(RAW_DIR, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Saved: {filename}")
        else:
            print(f"Failed: {filename} (Status {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {filename}: {e}")


if __name__ == "__main__":
    links = get_part_links()

    print(f"\nFound {len(links)} part files total.\n")

    for link in links:
        download_file(link)
