"""
Shared utilities for loading EMR data from CSV/Google Sheets.
"""

import hashlib
import logging
import re
from csv import DictReader
from io import StringIO
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """
    Normalize title by cleaning up punctuation.
    """
    if not title:
        return ""

    # Clean up the title first
    cleaned = title
    # Remove extra spaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Fix spacing around punctuation
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    cleaned = re.sub(r"\s*\(\s*", " (", cleaned)
    cleaned = re.sub(r"\s*\)\s*", ") ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*\.\s*", ". ", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    cleaned = re.sub(r"\s*\+\s*", "+", cleaned)
    cleaned = cleaned.strip()

    # Split by spaces and normalize each word
    words = cleaned.split()

    # Preserve uppercase for special abbreviations
    uppercase_words = {
        "X",
        "RAY",
        "AP",
        "LAT",
        "CT",
        "MRI",
        "ECG",
        "EKG",
        "IV",
        "OP",
        "IP",
        "ICU",
        "OPD",
        "IPD",
    }

    result = []
    for word in words:
        upper_word = word.upper()
        if upper_word in uppercase_words:
            result.append(upper_word)
        elif any(char in word for char in ["(", ")", "/", ","]):
            # Handle words with punctuation
            def replace_word_part(match):
                part = match.group(0)
                if part.upper() in uppercase_words:
                    return part.upper()
                return part.capitalize()

            result.append(re.sub(r"[a-zA-Z]+", replace_word_part, word))
        else:
            # Regular word capitalization
            result.append(word.capitalize())

    # Final cleanup
    final = " ".join(result)
    final = re.sub(r"\s+", " ", final)
    return final.strip()


def create_slug(name: str, ensure_unique: bool = False) -> str:
    """
    Create a slug from a name.
    Matches the TypeScript createSlug function.

    Args:
        name: The name to create a slug from.
        ensure_unique: If True, adds a UUID-based suffix to ensure uniqueness
                       even for identical titles.
    """
    import uuid

    if not name:
        return ""

    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s_-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    if ensure_unique:
        # Use UUID for guaranteed uniqueness
        unique_id = uuid.uuid4().hex[:16]
        slug = slug[:8]  # Keep first 8 chars of name
        slug = slug + "-" + unique_id
    else:
        slug = slug[:25]
        if len(slug) < 25:
            hash_suffix = hashlib.sha256(slug.encode()).hexdigest()
            needed_hash = 25 - len(slug) - 1
            slug = slug + "-" + hash_suffix[:needed_hash]

    return slug


def read_csv_from_file(file_path: str) -> list[dict[str, str]]:
    logger.info("Reading CSV from file: %s", file_path)
    with Path(file_path).open(encoding="utf-8-sig") as f:
        reader = DictReader(f)
        rows = list(reader)
    logger.info("Loaded %d rows from file", len(rows))
    return rows


def read_csv_from_url(url: str) -> list[dict[str, str]]:
    """Read CSV from a URL (including Google Sheets export URLs)."""
    logger.info("Reading CSV from URL: %s", url)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Parse CSV content
    csv_content = response.text
    # Remove BOM if present
    csv_content = csv_content.removeprefix("\ufeff")

    reader = DictReader(StringIO(csv_content))
    rows = list(reader)

    logger.info("Loaded %d rows from URL", len(rows))
    return rows


def read_csv_from_google_sheet(sheet_id: str, gid: str) -> list[dict[str, str]]:
    """Read CSV from Google Sheets using the export URL."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    )
    return read_csv_from_url(url)


def parse_code(
    code: str | None, system: str | None, display: str | None
) -> dict | None:
    """
    Parse code fields into a Code dict.
    Returns None if code or system is missing.
    """
    if not code or not system:
        return None

    # Clean up code - remove .0 suffix if present
    clean_code = str(code).strip()
    if "." in clean_code:
        if clean_code.endswith(".0"):
            clean_code = clean_code[:-2]
        else:
            # Handle cases like 42342.0-6 => 42342-6
            clean_code = clean_code.replace(".0", "")

    return {
        "system": system.strip(),
        "code": clean_code,
        "display": (display or clean_code).strip(),
    }


def write_output_csv(
    file_path: str, rows: list[dict], headers: list[str] | None = None
):
    """Write output CSV with results."""
    import csv

    if not rows:
        logger.warning("No rows to write to output CSV")
        return

    if headers is None:
        headers = list(rows[0].keys())

    output_dir = Path(file_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Writing output CSV to: %s", file_path)

    with Path(file_path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Output CSV written successfully")


def validate_code_against_valueset(valueset_slug: str, code: str, system: str) -> bool:
    """
    Validate a code against a valueset.
    Returns True if valid, False otherwise.
    """
    from care.emr.models.valueset import ValueSet
    from care.emr.resources.common.coding import Coding

    try:
        valueset = ValueSet.objects.filter(slug=valueset_slug).first()
        if not valueset:
            logger.warning("Valueset %s not found", valueset_slug)
            return False

        coding = Coding(code=code, system=system)
        return valueset.lookup(coding)
    except Exception as e:
        logger.error("Error validating code %s: %s", code, e)
        return False


def batch_validate_codes(
    valueset_slug: str, codes: list[tuple[str, str]]
) -> dict[str, bool]:
    """
    Batch validate codes against a valueset.
    Returns a dict mapping code -> is_valid.
    """
    results = {}
    for code, system in codes:
        results[code] = validate_code_against_valueset(valueset_slug, code, system)
    return results


def validate_and_substitute_code(
    code: str, system: str, valueset_slug: str, default_code: dict
) -> tuple[dict, str]:
    """
    Validate code against valueset and substitute with default if invalid.
    Returns (code_dict, substitution_message).
    """
    is_valid = validate_code_against_valueset(valueset_slug, code, system)

    if is_valid:
        return parse_code(code, system, code), ""

    # Use default code
    logger.warning(
        "Code %s not found in valueset %s, using default", code, valueset_slug
    )
    return default_code, f"{code} -> {default_code['code']}"


def ensure_category(category_name: str, facility, resource_type: str, created_by=None):
    """
    Ensure a ResourceCategory exists for the given name, if not create it.
    Returns the ResourceCategory object.
    Raises exceptions on database or validation errors.
    """
    from care.emr.models.resource_category import ResourceCategory

    try:
        category_title = normalize_title(category_name)
        category_slug_value = create_slug(category_name)
        category_slug = ResourceCategory.calculate_slug_from_facility(
            str(facility.external_id), category_slug_value
        )

        # Check if exists
        category = ResourceCategory.objects.filter(
            slug=category_slug, facility=facility
        ).first()

        if category:
            return category

        # Create new category
        category = ResourceCategory(
            facility=facility,
            resource_type=resource_type,
            resource_sub_type="other",
            title=category_title,
            slug=category_slug,
            description=f"Auto-generated category for {category_title}",
            created_by=created_by,
            updated_by=created_by,
        )
        category.save()
        logger.info("Created category: %s", category_title)
        return category

    except Exception as e:
        error_message = f"Failed to ensure category '{category_name}': {e}"
        raise RuntimeError(error_message) from e
