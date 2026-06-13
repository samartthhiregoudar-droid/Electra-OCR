import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parser import parse_voters  # noqa: E402


FIELDS = ["name", "fathers_name", "house_number", "age", "gender", "photo_status"]


def normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def f1_score(precision, recall):
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate_case(case):
    expected = {voter["voter_id"]: voter for voter in case["expected_voters"]}
    predicted = {voter["voter_id"]: voter for voter in parse_voters(case["ocr_lines"])}

    expected_ids = set(expected)
    predicted_ids = set(predicted)
    matched_ids = expected_ids & predicted_ids

    exact_matches = 0
    correct_fields = 0
    total_fields = 0

    for voter_id in expected_ids:
        expected_voter = expected[voter_id]
        predicted_voter = predicted.get(voter_id, {})
        record_is_exact = voter_id in predicted

        for field in FIELDS:
            if field not in expected_voter:
                continue
            total_fields += 1
            is_match = normalize(expected_voter.get(field)) == normalize(predicted_voter.get(field))
            correct_fields += int(is_match)
            record_is_exact = record_is_exact and is_match

        exact_matches += int(record_is_exact)

    precision = len(matched_ids) / len(predicted_ids) if predicted_ids else 0.0
    recall = len(matched_ids) / len(expected_ids) if expected_ids else 0.0

    return {
        "case_id": case["case_id"],
        "expected_records": len(expected_ids),
        "predicted_records": len(predicted_ids),
        "matched_records": len(matched_ids),
        "record_precision": precision,
        "record_recall": recall,
        "record_f1": f1_score(precision, recall),
        "exact_record_accuracy": exact_matches / len(expected_ids) if expected_ids else 0.0,
        "field_accuracy": correct_fields / total_fields if total_fields else 0.0,
    }


def average_metrics(case_results):
    metric_names = [
        "record_precision",
        "record_recall",
        "record_f1",
        "exact_record_accuracy",
        "field_accuracy",
    ]
    return {
        metric: sum(result[metric] for result in case_results) / len(case_results)
        for metric in metric_names
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate voter parser accuracy.")
    parser.add_argument(
        "--fixtures",
        default=PROJECT_ROOT / "data" / "evaluation_cases.json",
        type=Path,
        help="Path to JSON fixture file.",
    )
    args = parser.parse_args()

    with args.fixtures.open("r", encoding="utf-8") as fixture_file:
        cases = json.load(fixture_file)

    case_results = [evaluate_case(case) for case in cases]
    report = {
        "summary": average_metrics(case_results),
        "cases": case_results,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
