from collections import deque
from analytics.zscore import detect_zscore

class StatisticalAnomalyDetector:
    def __init__(self, window_size: int = 50) -> None:
        self.window_size = window_size
        self._window: deque[float] = deque(maxlen=window_size)

    def add_value(self, value: float) -> bool:
        self._window.append(value)
        return detect_zscore(list(self._window))
