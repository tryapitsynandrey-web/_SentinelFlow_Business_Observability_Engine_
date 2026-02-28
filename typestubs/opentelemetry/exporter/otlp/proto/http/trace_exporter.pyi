from typing import Any
from opentelemetry.sdk.trace.export import SpanExporter

class OTLPSpanExporter(SpanExporter):
    def __init__(self, **kwargs: Any) -> None: ...
