import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader


MANDATORY_FIELDS = [
    "policy_number",
    "policyholder_name",
    "incident_date",
    "incident_description",
    "claim_type",
    "estimated_damage",
    "attachments",
    "initial_estimate",
]

FRAUD_KEYWORDS = ("fraud", "inconsistent", "staged", "suspicious")


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_amount(raw: str) -> Optional[float]:
    cleaned = re.sub(r"[^0-9.]", "", raw)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_with_patterns(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def extract_fields(text: str) -> Tuple[Dict[str, object], List[str]]:
    fields: Dict[str, object] = {
        "policy_number": None,
        "policyholder_name": None,
        "effective_dates": None,
        "incident_date": None,
        "incident_time": None,
        "incident_location": None,
        "incident_description": None,
        "claimant": None,
        "third_parties": None,
        "contact_details": None,
        "asset_type": None,
        "asset_id": None,
        "estimated_damage": None,
        "claim_type": None,
        "attachments": None,
        "initial_estimate": None,
        "inconsistencies": [],
    }

    fields["policy_number"] = extract_with_patterns(
        text, [r"policy number[:\s]+([A-Za-z0-9\-]+)"]
    )
    fields["policyholder_name"] = extract_with_patterns(
        text, [r"policyholder name[:\s]+([A-Za-z ,.'-]+)"]
    )
    fields["effective_dates"] = extract_with_patterns(
        text,
        [r"(?:effective dates?|coverage period)[:\s]+([^\n]+)"],
    )
    fields["incident_date"] = extract_with_patterns(
        text,
        [
            r"(?:incident date|date of incident|date)[:\s]+([A-Za-z0-9\/\-, ]+)",
        ],
    )
    fields["incident_time"] = extract_with_patterns(
        text,
        [
            r"(?:incident time|time of incident|time)[:\s]+([0-9: ]+(?:am|pm|hrs)?)",
        ],
    )
    fields["incident_location"] = extract_with_patterns(
        text, [r"(?:incident location|location|place)[:\s]+([^\n]+)"]
    )
    fields["incident_description"] = extract_with_patterns(
        text, [r"(?:incident description|description)[:\s]+([^\n]+)"]
    )
    fields["claimant"] = extract_with_patterns(text, [r"claimant[:\s]+([^\n]+)"])
    fields["third_parties"] = extract_with_patterns(
        text, [r"(?:third parties|third party)[:\s]+([^\n]+)"]
    )
    fields["contact_details"] = extract_with_patterns(
        text,
        [
            r"(?:contact details|contact)[:\s]+([^\n]+)",
            r"([A-Za-z0-9_.+-]+@[A-Za-z0-9_.+-]+\.[A-Za-z]{2,})",
        ],
    )
    fields["asset_type"] = extract_with_patterns(
        text, [r"(?:asset type|property type)[:\s]+([^\n]+)"]
    )
    fields["asset_id"] = extract_with_patterns(
        text, [r"(?:asset id|asset identifier|vin)[:\s]+([^\n]+)"]
    )

    estimated = extract_with_patterns(
        text, [r"(?:estimated damage|damage estimate)[:\s]+\$?([0-9,\.]+)"]
    )
    fields["estimated_damage"] = parse_amount(estimated) if estimated else None

    claim_type = extract_with_patterns(text, [r"(?:claim type)[:\s]+([^\n]+)"])
    fields["claim_type"] = claim_type.lower() if claim_type else None

    attachments = extract_with_patterns(
        text, [r"(?:attachments?)[:\s]+([^\n]+)", r"(?:attached)[:\s]+([^\n]+)"]
    )
    if attachments:
        parts = [part.strip() for part in re.split(r"[;,]", attachments) if part.strip()]
        fields["attachments"] = parts

    initial_estimate = extract_with_patterns(
        text, [r"(?:initial estimate)[:\s]+\$?([0-9,\.]+)"]
    )
    fields["initial_estimate"] = parse_amount(initial_estimate) if initial_estimate else None

    if fields["initial_estimate"] and fields["estimated_damage"]:
        if fields["initial_estimate"] < fields["estimated_damage"] * 0.5:
            fields["inconsistencies"].append(
                "Initial estimate is far below estimated damage"
            )
    return fields, fields["inconsistencies"]


def detect_missing(fields: Dict[str, object]) -> List[str]:
    missing = []
    for key in MANDATORY_FIELDS:
        value = fields.get(key)
        if value is None or value == []:
            missing.append(key)
    return missing


def _is_negated(text: str, keyword: str) -> bool:
    return (
        re.search(rf"\b(?:no|not|without)\b[\w\s]{{0,20}}\b{keyword}\b", text)
        is not None
    )


def has_fraud_indicator(fields: Dict[str, object]) -> bool:
    desc = (fields.get("incident_description") or "").lower()
    for keyword in FRAUD_KEYWORDS:
        if re.search(rf"\b{keyword}\b", desc):
            if not _is_negated(desc, keyword):
                return True
    return False


def recommend_route(fields: Dict[str, object], missing: List[str]) -> Tuple[str, str]:
    reasons = []
    if missing:
        reasons.append(f"Missing fields: {', '.join(missing)}")
        return "Manual review", "; ".join(reasons)

    if has_fraud_indicator(fields):
        reasons.append("Description contains investigation keywords")
        return "Investigation", "; ".join(reasons)

    if (fields.get("claim_type") or "").strip().lower() == "injury":
        reasons.append("Claim type is injury")
        return "Specialist queue", "; ".join(reasons)

    estimate = fields.get("estimated_damage")
    if isinstance(estimate, (int, float)) and estimate < 25000:
        reasons.append(f"Estimated damage {estimate} < 25000")
        return "Fast-track", "; ".join(reasons)

    reasons.append("Default path")
    return "Standard review", "; ".join(reasons)


def process_file(path: Path) -> Dict[str, object]:
    text = read_text(path)
    fields, inconsistencies = extract_fields(text)
    missing = detect_missing(fields)
    route, reasoning = recommend_route(fields, missing)

    result = {
        "file": str(path),
        "extractedFields": fields,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reasoning,
    }
    if inconsistencies:
        result["extractedFields"]["inconsistencies"] = inconsistencies
    return result


def gather_files(input_path: Path) -> List[Path]:
    if input_path.is_dir():
        return sorted(
            [p for p in input_path.iterdir() if p.suffix.lower() in (".txt", ".pdf")]
        )
    return [input_path]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract FNOL fields and recommend routing."
    )
    parser.add_argument("--input", required=True, help="Path to FNOL file or directory")
    parser.add_argument("--output", help="Optional path to write JSON results")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input path not found: {input_path}")

    files = gather_files(input_path)
    if not files:
        raise SystemExit("No .txt or .pdf files found.")

    results = [process_file(path) for path in files]
    payload = results[0] if len(results) == 1 else results

    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2 if args.pretty else None)
        )
    else:
        print(json.dumps(payload, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

