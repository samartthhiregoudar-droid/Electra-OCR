import re


VOTER_ID_RE = re.compile(r"\b([A-Z]{3}[\dOIL]{7})\b", re.I)
FIELD_SPLIT_RE = re.compile(r"\s*[:\-]\s*")


def clean_text(value):
    """Normalize OCR text before field extraction."""
    value = str(value).replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,:;-")


def normalize_voter_id(raw_value):
    value = clean_text(raw_value).upper()
    match = VOTER_ID_RE.search(value)
    if not match:
        return None

    voter_id = match.group(1).upper()
    prefix = voter_id[:3]
    number = (
        voter_id[3:]
        .replace("O", "0")
        .replace("I", "1")
        .replace("L", "1")
    )
    return f"{prefix}{number}"


def field_value(line, label_pattern):
    match = re.search(label_pattern, line, re.I)
    if not match:
        return None

    remainder = line[match.end():]
    remainder = FIELD_SPLIT_RE.sub("", remainder, count=1)
    return clean_text(remainder)


def next_value(lines, index):
    if index + 1 >= len(lines):
        return ""

    candidate = clean_text(lines[index + 1])
    if not candidate:
        return ""
    if VOTER_ID_RE.search(candidate):
        return ""
    if re.search(r"\b(Name|House|Age|Gender|Photo)\b", candidate, re.I):
        return ""
    return candidate


def append_current(voters, current):
    if current.get("voter_id"):
        voters.append(current.copy())


def parse_voters(lines):
    voters = []
    current = {}

    normalized_lines = [clean_text(line) for line in lines if clean_text(line)]

    for index, line in enumerate(normalized_lines):
        voter_id = normalize_voter_id(line)
        if voter_id:
            append_current(voters, current)
            current = {"voter_id": voter_id}
            continue

        if not current:
            continue

        if re.search(r"\b(?:Name|Elector'?s Name|Name of Elector)\b", line, re.I) and not re.search(
            r"\b(?:Father|Husband|Mother|Guardian)\b", line, re.I
        ):
            value = field_value(line, r"\b(?:Name|Elector'?s Name|Name of Elector)\b") or next_value(
                normalized_lines, index
            )
            if value:
                current["name"] = value
            continue

        relation_value = field_value(
            line,
            r"\b(?:Father|Husband|Mother|Guardian)'?s?\s*Name\b",
        )
        if relation_value is not None:
            value = relation_value or next_value(normalized_lines, index)
            if value:
                current["fathers_name"] = value
            continue

        house_match = re.search(
            r"\bHouse\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\s/\-]*)",
            line,
            re.I,
        )
        if house_match:
            current["house_number"] = clean_text(house_match.group(1))
            continue

        age_match = re.search(r"\bAge\s*[:\-]?\s*(\d{1,3})\b", line, re.I)
        if age_match:
            current["age"] = int(age_match.group(1))

        gender_match = re.search(r"\b(Male|Female|Other)\b", line, re.I)
        if gender_match:
            current["gender"] = gender_match.group(1).capitalize()

        if re.search(r"\bPhoto\b.*\bAvailable\b", line, re.I):
            current["photo_status"] = "Available"
        elif re.search(r"\bPhoto\b.*\b(?:Not Available|Unavailable)\b", line, re.I):
            current["photo_status"] = "Not Available"

    append_current(voters, current)
    return voters
