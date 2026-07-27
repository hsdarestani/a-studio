from copy import deepcopy

CREDIT_COSTS = {"micro": 0, "small": 1, "standard": 3, "advanced": 7, "custom": 12}

PLANS = {
    "starter": {"name": "Starter", "monthly": 49, "credits": 3, "projects": 1},
    "business": {"name": "Business", "monthly": 149, "credits": 12, "projects": 5},
    "pro": {"name": "Pro", "monthly": 399, "credits": 40, "projects": 25},
}


def estimate_size(before, after):
    before = before or {}
    after = after or {}
    if before == after:
        return "micro"
    before_features = set(before.get("features", []))
    after_features = set(after.get("features", []))
    added = after_features - before_features
    sections_before = before.get("sections", [])
    sections_after = after.get("sections", [])
    delta = abs(len(sections_after) - len(sections_before))
    advanced = {"payments", "marketplace", "chat", "location", "external_api", "membership", "booking"}
    if added & advanced:
        return "advanced"
    if len(added) >= 2 or delta >= 3:
        return "standard"
    if added or delta:
        return "small"
    return "micro"


def cost_for_size(size):
    return CREDIT_COSTS.get(size, CREDIT_COSTS["custom"])


def merge_plan_metadata(plan_key, metadata=None):
    result = deepcopy(PLANS.get(plan_key, PLANS["starter"]))
    result.update(metadata or {})
    return result
