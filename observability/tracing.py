from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

def configure_tracing(service_name: str, otlp_endpoint: str) -> None:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    AioHttpClientInstrumentor().instrument()

def get_tracer() -> trace.Tracer:
    return trace.get_tracer("sentinelflow")
