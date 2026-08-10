import os
import re
import shutil
import requests

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# Requests session with automatic retries
# ============================================================

session = requests.Session()

retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503],
    allowed_methods=["GET"],
)

adapter = HTTPAdapter(max_retries=retry)

session.mount("https://", adapter)
session.mount("http://", adapter)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}


# ============================================================
# Download HTML
# ============================================================

def get_html(url):

    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=(10, 60)
        )

        response.raise_for_status()

        # Make sure Arabic text is decoded correctly
        response.encoding = (
            response.apparent_encoding
            or response.encoding
        )

        return response.text

    except requests.exceptions.RequestException as e:

        print(f"Failed to retrieve: {url}")
        print(f"Error: {e}")

        return None


# ============================================================
# Clean directory name
# ============================================================

def clean_directory_name(name):

    """
    Make the Surah name safe to use as a directory name.
    """

    # Replace filesystem-invalid characters
    name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        name
    )

    # Normalize whitespace
    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    # Remove trailing dots/spaces
    name = name.rstrip(". ")

    return name


# ============================================================
# Arabic normalization
# ============================================================

def normalize_arabic(text):

    """
    Normalize Arabic text for comparison.

    Examples:

        سُورَةُ البَقَرَة
        سورة البقرة

    become equivalent.
    """

    if not text:
        return ""

    text = text.strip()

    # --------------------------------------------------------
    # Remove Arabic diacritics / tashkeel
    # --------------------------------------------------------

    text = re.sub(
        r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]',
        '',
        text
    )

    # --------------------------------------------------------
    # Normalize Arabic letters
    # --------------------------------------------------------

    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ٱ", "ا")

    text = text.replace("ى", "ي")

    # Keep ة as ة.
    # Do NOT convert it to ه because that can create
    # incorrect matches between different Arabic words.

    # Remove tatweel
    text = text.replace("ـ", "")

    # --------------------------------------------------------
    # Normalize سورة variations
    # --------------------------------------------------------

    text = re.sub(
        r'^\s*سُ?و?ر?َ?ة[َُِّْ]?\s+',
        'سورة ',
        text
    )

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    text = re.sub(
        r'\s+',
        ' ',
        text
    ).strip()

    # --------------------------------------------------------
    # Remove punctuation
    # --------------------------------------------------------

    text = re.sub(
        r'[،,:;.!؟|()\[\]{}"\'\-–—_]+',
        ' ',
        text
    )

    text = re.sub(
        r'\s+',
        ' ',
        text
    ).strip()

    return text


# ============================================================
# Extract Surah core name
# ============================================================

def extract_surah_core_name(name):

    """
    Extract the actual Surah name from a page title.

    Examples:

        سورة البقرة
        سورة البقرة مكتوبة مصورة من مصحف المدينة
        سورة محمد صلى الله عليه وسلم
        سورة محمد صلى الله عليه وسلم رقم 510
        سورة محمد الصفحة 510

    All should resolve to:

        البقرة
        محمد
    """

    if not name:
        return ""

    name = normalize_arabic(name)

    # --------------------------------------------------------
    # Remove "سورة" from beginning
    # --------------------------------------------------------

    name = re.sub(
        r'^\s*سورة\s*',
        '',
        name
    ).strip()

    # --------------------------------------------------------
    # Remove page-number information
    # --------------------------------------------------------

    name = re.sub(
        r'\s+(?:رقم|الرقم)\s+\d+.*$',
        '',
        name
    ).strip()

    name = re.sub(
        r'\s+(?:الصفحة|صفحة)\s+(?:رقم\s*)?\d+.*$',
        '',
        name
    ).strip()

    # --------------------------------------------------------
    # Remove common descriptive text
    # --------------------------------------------------------

    descriptive_patterns = [

        r'\s+مكتوبة.*$',
        r'\s+مصور[ةه].*$',
        r'\s+مصورة.*$',
        r'\s+من\s+مصحف.*$',
        r'\s+مصحف\s+المدينة.*$',
        r'\s+مصحف\s+المدينه.*$',
        r'\s+برواية.*$',
        r'\s+رواية.*$',
        r'\s+روايه.*$',
        r'\s+حفص.*$',
        r'\s+عن\s+عاصم.*$',
        r'\s+المدينة\s+المنورة.*$',
        r'\s+المدينه\s+المنوره.*$',
        r'\s+القرآن.*$',
        r'\s+القران.*$',
    ]

    for pattern in descriptive_patterns:

        name = re.sub(
            pattern,
            '',
            name,
            flags=re.IGNORECASE
        ).strip()

    # --------------------------------------------------------
    # Remove "صلى الله عليه وسلم" and similar additions
    # --------------------------------------------------------

    name = re.sub(
        r'\s+صلى\s+الله\s+عليه\s+وسلم.*$',
        '',
        name
    ).strip()

    name = re.sub(
        r'\s+صلّى\s+الله\s+عليه\s+وسلّم.*$',
        '',
        name
    ).strip()

    # --------------------------------------------------------
    # Remove separators and anything after them
    # --------------------------------------------------------

    name = re.sub(
        r'\s*[-–—|:]\s*.*$',
        '',
        name
    ).strip()

    # --------------------------------------------------------
    # Final whitespace cleanup
    # --------------------------------------------------------

    name = re.sub(
        r'\s+',
        ' ',
        name
    ).strip()

    return name

# ============================================================
# Surah comparison key
# ============================================================

def get_surah_key(name):

    """
    Return a normalized key used to determine whether two
    directory names represent the same Surah.
    """

    core = extract_surah_core_name(name)

    core = normalize_arabic(core)

    return core


# ============================================================
# Extract Surah name
# ============================================================

def extract_surah_name(html, surah_number):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ========================================================
    # Get all page text
    # ========================================================

    page_text = soup.get_text(
        " ",
        strip=True
    )

    page_text = re.sub(
        r"\s+",
        " ",
        page_text
    ).strip()

    # ========================================================
    # Method 1:
    # Look for:
    #
    # سورة XXXXX الصفحة رقم 123
    # ========================================================

    match = re.search(
        r"(سورة\s+.+?)\s+الصفحة(?:\s+رقم)?\s+\d+",
        page_text
    )

    if match:

        surah_name = match.group(1).strip()

        return clean_directory_name(
            surah_name
        )

    # ========================================================
    # Method 2:
    # Try <title>
    # ========================================================

    if soup.title:

        title = soup.title.get_text(
            " ",
            strip=True
        )

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

        title = re.sub(
            r"\s+الصفحة(?:\s+رقم)?\s+\d+.*$",
            "",
            title
        ).strip()

        # Remove common website names

        title = re.sub(
            r"\s*[-|]\s*"
            r"(المكتبة الشاملة|المكتبة الإسلامية|Islamic Book)"
            r".*?$",
            "",
            title,
            flags=re.IGNORECASE
        ).strip()

        if title:

            # Make sure we are actually extracting a Surah
            if "سورة" in title:

                return clean_directory_name(
                    title
                )

    # ========================================================
    # Method 3:
    # Search headings
    # ========================================================

    for tag in soup.find_all(
        ["h1", "h2", "h3"]
    ):

        text = tag.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        if not text:
            continue

        if text == "بسم الله الرحمن الرحيم":
            continue

        # ----------------------------------------------------
        # Remove page information
        # ----------------------------------------------------

        text = re.sub(
            r"\s+الصفحة(?:\s+رقم)?\s+\d+.*$",
            "",
            text
        ).strip()

        # ----------------------------------------------------
        # Extract Surah
        # ----------------------------------------------------

        match = re.search(
            r"(سورة\s+.+)",
            text
        )

        if match:

            surah_name = match.group(1).strip()

            return clean_directory_name(
                surah_name
            )

    # ========================================================
    # Method 4:
    # Search entire page
    # ========================================================

    match = re.search(
        r"(سورة\s+.+?)\s+الصفحة\s+\d+",
        page_text
    )

    if match:

        name = match.group(1).strip()

        return clean_directory_name(
            name
        )

    # ========================================================
    # Method 5:
    # Generic سورة fallback
    # ========================================================

    match = re.search(
        r"(?:سورة|سُورَة)\s+"
        r"([^،,:;.!؟|()\[\]]{2,80})",
        page_text
    )

    if match:

        name = match.group(1).strip()

        if name:

            return clean_directory_name(
                "سورة " + name
            )

    # ========================================================
    # Final fallback
    # ========================================================

    return f"surah_{surah_number}"


# ============================================================
# Find existing Surah directory
# ============================================================

def find_surah_directory(
    output_directory,
    surah_name
):
    """
    Find an existing directory representing the same Surah.

    If a matching directory has a descriptive name such as:

        سورة البقرة مكتوبة مصورة من مصحف المدينة

    while the newly detected name is:

        سورة البقرة

    the existing directory is renamed to the clean Surah name:

        سورة البقرة
    """

    target_key = get_surah_key(surah_name)

    if not target_key:
        return None

    if not os.path.exists(output_directory):
        return None

    # --------------------------------------------------------
    # Desired clean directory name
    # --------------------------------------------------------

    clean_name = clean_directory_name(
        "سورة " + extract_surah_core_name(surah_name)
    )

    clean_directory = os.path.join(
        output_directory,
        clean_name
    )

    # --------------------------------------------------------
    # First check whether the clean folder already exists
    # --------------------------------------------------------

    if os.path.isdir(clean_directory):

        return clean_directory

    # --------------------------------------------------------
    # Search for descriptive/old folder names
    # --------------------------------------------------------

    for directory_name in os.listdir(
        output_directory
    ):

        directory_path = os.path.join(
            output_directory,
            directory_name
        )

        if not os.path.isdir(directory_path):
            continue

        existing_key = get_surah_key(
            directory_name
        )

        if existing_key != target_key:
            continue

        # ----------------------------------------------------
        # Same Surah found under another name.
        #
        # Rename it to the clean Surah name.
        # ----------------------------------------------------

        print()
        print(
            "    Matching Surah folder found:"
        )

        print(
            f"        Old: {directory_path}"
        )

        print(
            f"        New: {clean_directory}"
        )

        try:

            os.rename(
                directory_path,
                clean_directory
            )

            print(
                "    Folder renamed successfully."
            )

            return clean_directory

        except OSError as e:

            print(
                f"    Could not rename folder: {e}"
            )

            # If rename failed, continue using
            # the existing directory.
            return directory_path

    return None


# ============================================================
# Download image
# ============================================================

def download_image(
    image_url,
    save_directory,
    page_number
):

    try:

        response = session.get(
            image_url,
            headers=HEADERS,
            timeout=(10, 60)
        )

        response.raise_for_status()

        # ----------------------------------------------------
        # Save using page number
        #
        # Example:
        #
        # page_42.png
        # page_43.png
        # ----------------------------------------------------

        image_name = (
            f"page_{page_number:03d}.png"
        )

        image_path = os.path.join(
            save_directory,
            image_name
        )

        with open(
            image_path,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        print(
            f"    Image saved: {image_path}"
        )

        return True

    except requests.exceptions.RequestException as e:

        print(
            f"    Failed to download image: "
            f"{image_url}"
        )

        print(
            f"    Error: {e}"
        )

        return False


# ============================================================
# Check whether page exists
# ============================================================

def page_exists(url):

    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=(10, 60)
        )

        if response.status_code == 200:
            return True

        return False

    except requests.exceptions.RequestException:

        return False


# ============================================================
# Move files from one directory into another
# ============================================================

def merge_directories(
    source_directory,
    destination_directory
):

    """
    Merge source_directory into destination_directory.

    Existing files in destination are NOT overwritten.

    If a filename already exists, the source file gets a
    numbered alternative name.
    """

    if not os.path.isdir(
        source_directory
    ):
        return

    os.makedirs(
        destination_directory,
        exist_ok=True
    )

    print()
    print(
        f"    Merging directory:"
    )
    print(
        f"        From: {source_directory}"
    )
    print(
        f"        To  : {destination_directory}"
    )

    for filename in os.listdir(
        source_directory
    ):

        source_path = os.path.join(
            source_directory,
            filename
        )

        destination_path = os.path.join(
            destination_directory,
            filename
        )

        # ----------------------------------------------------
        # File
        # ----------------------------------------------------

        if os.path.isfile(
            source_path
        ):

            if not os.path.exists(
                destination_path
            ):

                shutil.move(
                    source_path,
                    destination_path
                )

                print(
                    f"        Moved: {filename}"
                )

            else:

                # ------------------------------------------------
                # Do not overwrite existing file
                # ------------------------------------------------

                base, extension = os.path.splitext(
                    filename
                )

                counter = 1

                while True:

                    new_filename = (
                        f"{base}_duplicate_{counter}"
                        f"{extension}"
                    )

                    new_destination = os.path.join(
                        destination_directory,
                        new_filename
                    )

                    if not os.path.exists(
                        new_destination
                    ):
                        break

                    counter += 1

                shutil.move(
                    source_path,
                    new_destination
                )

                print(
                    f"        Renamed duplicate:"
                    f" {filename} -> {new_filename}"
                )

        # ----------------------------------------------------
        # Subdirectory
        # ----------------------------------------------------

        elif os.path.isdir(
            source_path
        ):

            destination_subdirectory = os.path.join(
                destination_directory,
                filename
            )

            merge_directories(
                source_path,
                destination_subdirectory
            )

    # --------------------------------------------------------
    # Remove empty source directory
    # --------------------------------------------------------

    try:

        if not os.listdir(
            source_directory
        ):

            os.rmdir(
                source_directory
            )

            print(
                f"        Removed empty directory:"
                f" {source_directory}"
            )

    except OSError:
        pass


# ============================================================
# Merge duplicate Surah folders already on disk
# ============================================================

def merge_duplicate_surah_directories(
    output_directory
):

    """
    Scan the Quran directory and merge folders that represent
    the same Surah.

    Example:

        سورة البقرة
        سورة البقرة مكتوبة مصورة من مصحف المدينة

    becomes:

        سورة البقرة

    with all images merged into it.
    """

    if not os.path.isdir(
        output_directory
    ):
        return

    directories = [
        name
        for name in os.listdir(
            output_directory
        )
        if os.path.isdir(
            os.path.join(
                output_directory,
                name
            )
        )
    ]

    grouped = {}

    # --------------------------------------------------------
    # Group directories by normalized Surah identity
    # --------------------------------------------------------

    for directory_name in directories:

        key = get_surah_key(
            directory_name
        )

        if not key:
            continue

        grouped.setdefault(
            key,
            []
        ).append(
            directory_name
        )

    # --------------------------------------------------------
    # Merge groups containing more than one directory
    # --------------------------------------------------------

    for key, directory_names in grouped.items():

        if len(directory_names) <= 1:
            continue

        print()
        print("=" * 70)
        print(
            "Duplicate Surah folders detected"
        )
        print(
            f"Surah key: {key}"
        )

        # ----------------------------------------------------
        # Choose the shortest/cleanest name as the destination.
        #
        # Example:
        #
        # سورة البقرة
        # سورة البقرة مكتوبة مصورة من مصحف المدينة
        #
        # Destination:
        #
        # سورة البقرة
        # ----------------------------------------------------

        destination_name = min(
            directory_names,
            key=lambda x: len(
                normalize_arabic(x)
            )
        )

        destination_directory = os.path.join(
            output_directory,
            destination_name
        )

        print(
            f"Keeping: {destination_name}"
        )

        # ----------------------------------------------------
        # Merge all other directories
        # ----------------------------------------------------

        for source_name in directory_names:

            if source_name == destination_name:
                continue

            source_directory = os.path.join(
                output_directory,
                source_name
            )

            merge_directories(
                source_directory,
                destination_directory
            )


# ============================================================
# Main downloader
# ============================================================

def download_quran():

    base_url = (
        "https://www.islamicbook.ws/6/"
    )

    output_directory = "Quran"

    # --------------------------------------------------------
    # Create main Quran directory
    # --------------------------------------------------------

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    print("=" * 70)
    print("Quran downloader")
    print("=" * 70)

    # --------------------------------------------------------
    # Start from page 1
    # --------------------------------------------------------

    i = 1

    # --------------------------------------------------------
    # Keep track of the current Surah
    #
    # The number is assigned automatically:
    #
    # 01 = first Surah encountered
    # 02 = second Surah encountered
    # 03 = third Surah encountered
    # ...
    # --------------------------------------------------------

    current_surah_key = None
    current_surah_number = 0
    current_surah_directory = None

    # --------------------------------------------------------
    # Scan existing folders first
    # --------------------------------------------------------

    print()
    print(
        "Checking existing Surah directories..."
    )

    merge_duplicate_surah_directories(
        output_directory
    )

    # --------------------------------------------------------
    # Main download loop
    # --------------------------------------------------------

    while True:

        html_url = (
            f"{base_url}{i}.html"
        )

        image_url = (
            f"{base_url}{i}.png"
        )

        print()
        print("-" * 70)
        print(
            f"Processing page #{i}"
        )

        print(
            f"HTML: {html_url}"
        )

        # ----------------------------------------------------
        # Get HTML
        # ----------------------------------------------------

        html = get_html(
            html_url
        )

        # ----------------------------------------------------
        # If page does not exist, stop
        # ----------------------------------------------------

        if html is None:

            print()
            print(
                f"Page #{i} does not exist "
                f"or could not be downloaded."
            )

            print(
                "Stopping."
            )

            break

        # ----------------------------------------------------
        # Extract Surah name
        # ----------------------------------------------------

        surah_name = extract_surah_name(
            html,
            i
        )

        surah_key = get_surah_key(
            surah_name
        )

        print(
            f"    Detected Surah: {surah_name}"
        )

        print(
            f"    Surah key: {surah_key}"
        )

        # ====================================================
        # NEW SURAH
        # ====================================================

        if surah_key != current_surah_key:

            current_surah_number += 1

            current_surah_key = surah_key

            # ------------------------------------------------
            # Get the clean Surah name
            # ------------------------------------------------

            surah_core_name = extract_surah_core_name(
                surah_name
            )

            # ------------------------------------------------
            # Create numbered folder name
            #
            # Example:
            #
            # 01-سورة الفاتحة
            # 02-سورة البقرة
            # 03-سورة آل عمران
            # ------------------------------------------------

            folder_name = (
                f"{current_surah_number:02d}-"
                f"سورة {surah_core_name}"
            )

            desired_directory = os.path.join(
                output_directory,
                folder_name
            )

            # ------------------------------------------------
            # Check whether an existing folder represents
            # this Surah.
            #
            # This handles:
            #
            # سورة البقرة
            #
            # and:
            #
            # سورة البقرة مكتوبة مصورة من مصحف المدينة
            # ------------------------------------------------

            existing_directory = find_surah_directory(
                output_directory,
                surah_name
            )

            if existing_directory is not None:

                # ------------------------------------------------
                # If existing folder already has the correct
                # numbered name, simply use it.
                # ------------------------------------------------

                if (
                    os.path.abspath(existing_directory)
                    == os.path.abspath(desired_directory)
                ):

                    current_surah_directory = (
                        existing_directory
                    )

                else:

                    # ------------------------------------------------
                    # Rename/move old folder to numbered folder
                    # ------------------------------------------------

                    print()
                    print(
                        "    Existing Surah folder found:"
                    )

                    print(
                        f"        Old: "
                        f"{existing_directory}"
                    )

                    print(
                        f"        New: "
                        f"{desired_directory}"
                    )

                    # ------------------------------------------------
                    # If desired directory already exists,
                    # merge into it.
                    # ------------------------------------------------

                    if os.path.exists(
                        desired_directory
                    ):

                        merge_directories(
                            existing_directory,
                            desired_directory
                        )

                        current_surah_directory = (
                            desired_directory
                        )

                    else:

                        try:

                            os.rename(
                                existing_directory,
                                desired_directory
                            )

                            print(
                                "    Folder renamed successfully."
                            )

                            current_surah_directory = (
                                desired_directory
                            )

                        except OSError as e:

                            print(
                                f"    Could not rename folder: {e}"
                            )

                            # Fall back to existing directory
                            current_surah_directory = (
                                existing_directory
                            )

            else:

                # ------------------------------------------------
                # No existing folder.
                # Create the numbered folder.
                # ------------------------------------------------

                os.makedirs(
                    desired_directory,
                    exist_ok=True
                )

                current_surah_directory = (
                    desired_directory
                )

                print(
                    f"    New directory: "
                    f"{current_surah_directory}"
                )

            print(
                f"    Surah number: "
                f"{current_surah_number:02d}"
            )

            print(
                f"    Directory: "
                f"{current_surah_directory}"
            )

        # ====================================================
        # SAME SURAH
        # ====================================================

        else:

            print(
                f"    Same Surah - using:"
                f" {current_surah_directory}"
            )

        # ----------------------------------------------------
        # Download page image
        # ----------------------------------------------------

        download_image(
            image_url,
            current_surah_directory,
            i
        )

        # ----------------------------------------------------
        # Next page
        # ----------------------------------------------------

        i += 1

    # ========================================================
    # Final cleanup
    # ========================================================

    print()
    print(
        "Performing final duplicate-folder cleanup..."
    )

    merge_duplicate_surah_directories(
        output_directory
    )

    print()
    print("=" * 70)
    print("Download completed.")
    print("=" * 70)




# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    download_quran()

