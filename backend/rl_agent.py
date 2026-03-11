def route_decision(congestion):
    rewards = {
        "LOW": 10,
        "MEDIUM": 3,
        "HIGH": -5
    }

    if rewards[congestion] < 0:
        return "ALTERNATE_ROUTE"
    return "NORMAL_ROUTE"