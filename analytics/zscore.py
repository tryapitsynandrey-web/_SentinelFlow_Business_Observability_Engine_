import math

def detect_zscore(values: list[float], threshold: float = 3.0) -> bool:
    if len(values) < 2:
        return False
        
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    
    if variance == 0:
        return False
        
    std_dev = math.sqrt(variance)
    last_value = values[-1]
    
    z_score = abs(last_value - mean) / std_dev
    return z_score > threshold
