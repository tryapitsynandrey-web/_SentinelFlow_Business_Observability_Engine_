def compute_ewma(values: list[float], alpha: float = 0.3) -> float:
    if not values:
        return 0.0
        
    ewma = values[0]
    for value in values[1:]:
        ewma = alpha * value + (1 - alpha) * ewma
        
    return ewma
