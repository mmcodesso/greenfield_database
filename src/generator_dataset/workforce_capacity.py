from __future__ import annotations

from collections import Counter, defaultdict


DIRECT_MANUFACTURING_TITLES = (
    "Assembler",
    "Machine Operator",
    "Quality Technician",
)

DIRECT_WORK_CENTER_CODES = (
    "ASSEMBLY",
    "FINISH",
    "CUT",
    "PACK",
    "QA",
)

STANDARD_MANUFACTURING_SHIFT_HOURS = 8.0
CAPACITY_SHARE_TARGET_BLEND = 0.50

DIRECT_WORK_CENTER_TARGET_SHARES = {
    "ASSEMBLY": 0.42,
    "FINISH": 0.22,
    "CUT": 0.21,
    "PACK": 0.12,
    "QA": 0.03,
}

DIRECT_TITLE_WORK_CENTER_WEIGHTS = {
    "Assembler": {
        "ASSEMBLY": 0.50,
        "FINISH": 0.25,
        "PACK": 0.25,
    },
    "Machine Operator": {
        "CUT": 0.55,
        "ASSEMBLY": 0.45,
    },
    "Quality Technician": {
        "FINISH": 0.56,
        "QA": 0.11,
        "ASSEMBLY": 0.33,
    },
}


def _normalized_weights(weights: dict[str, float]) -> dict[str, float]:
    filtered = {
        str(work_center_code): float(weight)
        for work_center_code, weight in weights.items()
        if float(weight) > 0
    }
    total_weight = sum(filtered.values())
    if total_weight <= 0:
        return {}
    return {
        work_center_code: float(weight) / total_weight
        for work_center_code, weight in filtered.items()
    }


def smooth_weighted_rotation(weights: dict[str, float], count: int) -> list[str]:
    if count <= 0:
        return []

    normalized = _normalized_weights(weights)
    if not normalized:
        return []

    current_weight = {work_center_code: 0.0 for work_center_code in normalized}
    total_weight = sum(normalized.values())
    sequence: list[str] = []
    for _ in range(int(count)):
        for work_center_code, weight in normalized.items():
            current_weight[work_center_code] += weight
        selected = max(
            normalized,
            key=lambda work_center_code: (
                current_weight[work_center_code],
                normalized[work_center_code],
                -DIRECT_WORK_CENTER_CODES.index(work_center_code)
                if work_center_code in DIRECT_WORK_CENTER_CODES
                else 0,
            ),
        )
        sequence.append(selected)
        current_weight[selected] -= total_weight
    return sequence


def direct_work_center_assignments(worker_keys_and_titles: list[tuple[int, str]]) -> dict[int, str]:
    grouped_workers: dict[str, list[int]] = defaultdict(list)
    for worker_key, job_title in sorted(worker_keys_and_titles, key=lambda value: (str(value[1]), int(value[0]))):
        if str(job_title) not in DIRECT_TITLE_WORK_CENTER_WEIGHTS:
            continue
        grouped_workers[str(job_title)].append(int(worker_key))

    assignments: dict[int, str] = {}
    for job_title, worker_keys in grouped_workers.items():
        rotation = smooth_weighted_rotation(
            DIRECT_TITLE_WORK_CENTER_WEIGHTS[str(job_title)],
            len(worker_keys),
        )
        for worker_key, work_center_code in zip(sorted(worker_keys), rotation, strict=False):
            assignments[int(worker_key)] = str(work_center_code)
    return assignments


def work_center_counts_from_codes(work_center_codes: list[str]) -> dict[str, int]:
    counts = Counter(str(work_center_code) for work_center_code in work_center_codes if str(work_center_code))
    return {
        work_center_code: int(counts.get(work_center_code, 0))
        for work_center_code in DIRECT_WORK_CENTER_CODES
    }


def work_center_shares_from_counts(work_center_counts: dict[str, int | float]) -> dict[str, float]:
    normalized_counts = {
        work_center_code: float(work_center_counts.get(work_center_code, 0.0))
        for work_center_code in DIRECT_WORK_CENTER_CODES
    }
    total_count = sum(normalized_counts.values())
    if total_count <= 0:
        return {
            work_center_code: float(DIRECT_WORK_CENTER_TARGET_SHARES[work_center_code])
            for work_center_code in DIRECT_WORK_CENTER_CODES
        }
    return {
        work_center_code: float(normalized_counts[work_center_code]) / total_count
        for work_center_code in DIRECT_WORK_CENTER_CODES
    }


def blended_capacity_shares(
    work_center_counts: dict[str, int | float],
    blend_to_target: float = CAPACITY_SHARE_TARGET_BLEND,
) -> dict[str, float]:
    assignment_shares = work_center_shares_from_counts(work_center_counts)
    blend = max(0.0, min(float(blend_to_target), 1.0))
    blended = {
        work_center_code: (
            assignment_shares[work_center_code] * (1.0 - blend)
            + float(DIRECT_WORK_CENTER_TARGET_SHARES[work_center_code]) * blend
        )
        for work_center_code in DIRECT_WORK_CENTER_CODES
    }
    total_share = sum(blended.values()) or 1.0
    return {
        work_center_code: float(blended[work_center_code]) / total_share
        for work_center_code in DIRECT_WORK_CENTER_CODES
    }


def allocate_hours_by_work_center(total_hours: float, work_center_shares: dict[str, float]) -> dict[str, float]:
    normalized_shares = work_center_shares_from_counts(work_center_shares)
    remaining_hours = round(float(total_hours), 2)
    allocations: dict[str, float] = {}
    ordered_codes = list(DIRECT_WORK_CENTER_CODES)
    for index, work_center_code in enumerate(ordered_codes):
        if index == len(ordered_codes) - 1:
            allocations[work_center_code] = round(max(remaining_hours, 0.0), 2)
            break
        allocated_hours = round(float(total_hours) * float(normalized_shares[work_center_code]), 2)
        allocations[work_center_code] = allocated_hours
        remaining_hours = round(remaining_hours - allocated_hours, 2)
    return allocations
