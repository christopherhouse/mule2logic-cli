"""OpenTelemetry instrumentation for the m2la-api service.

Provides two modes:

1. **Azure Monitor** — when ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is set,
   ``configure_azure_monitor()`` auto-instruments FastAPI, logging, httpx, and
   Azure SDK calls and exports traces, metrics, and logs to Application Insights.

2. **Local dev** — when the connection string is absent, the OTel SDK is
   configured with a console exporter so developers see spans locally.

.. important::

   ``init_telemetry()`` **must** be called before importing ``fastapi.FastAPI``
   so that the distro can monkey-patch the framework.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

_TELEMETRY_INITIALIZED = False


def _configure_logging() -> None:
    """Configure Python logging to output to console.

    Sets up a StreamHandler with formatting and configures the root logger
    to output INFO-level logs by default. The log level can be overridden
    via the LOG_LEVEL environment variable.
    """
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing configuration
    )


def init_telemetry(*, service_name: str = "m2la-api", service_version: str = "0.1.0") -> None:
    """Bootstrap OpenTelemetry instrumentation.

    Call this **once** at application startup, before any ``FastAPI`` import.
    """
    global _TELEMETRY_INITIALIZED  # noqa: PLW0603
    if _TELEMETRY_INITIALIZED:
        return
    _TELEMETRY_INITIALIZED = True

    # Configure Python logging first
    _configure_logging()

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

    if connection_string:
        _init_azure_monitor(connection_string, service_name=service_name, service_version=service_version)
    else:
        _init_local_dev(service_name=service_name, service_version=service_version)


def _init_azure_monitor(
    connection_string: str,
    *,
    service_name: str,
    service_version: str,
) -> None:
    """Configure the Azure Monitor OpenTelemetry distro."""
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )

    configure_azure_monitor(
        connection_string=connection_string,
        resource=resource,
    )
    logger.info(
        "Azure Monitor OpenTelemetry configured (service=%s, version=%s)",
        service_name,
        service_version,
    )
    tracer = trace.get_tracer(service_name)
    # Emit a startup span so we know the pipeline is healthy.
    with tracer.start_as_current_span("m2la.api.startup"):
        logger.info("Telemetry startup span emitted")


def _init_local_dev(*, service_name: str, service_version: str) -> None:
    """Configure vanilla OTel SDK with console exporter for local development."""
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
            }
        )

        # Traces
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

        # Metrics
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60_000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)

        logger.info("Local-dev OTel configured with console exporters (service=%s)", service_name)
    except ImportError:
        logger.warning("OpenTelemetry SDK not available — telemetry disabled for local dev")
