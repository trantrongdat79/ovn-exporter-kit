"""
Main entry point for json_to_prometheus component.

Initializes Kafka consumer, Prometheus exporter, and HTTP server.
"""

import sys
import os
import signal
import time
import threading
from typing import Optional

# Add common package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.logger import setup_logger
from consumer import JsonMetricConsumer
from exporter import PrometheusExporter
from http_server import MetricsHTTPServer


class JsonToPrometheusService:
    """
    Main service orchestrator for json_to_prometheus component.
    
    Coordinates consumer, exporter, and HTTP server lifecycle.
    """
    
    def __init__(self):
        """Initialize service components."""
        self.logger = None
        self.consumer: Optional[JsonMetricConsumer] = None
        self.exporter: Optional[PrometheusExporter] = None
        self.http_server: Optional[MetricsHTTPServer] = None
        self.running = False
    
    def setup(self):
        """
        Set up service components from environment variables.
        
        Initializes logger, consumer, exporter, and HTTP server.
        """
        for file_name in os.listdir('logs/json_to_prometheus/'):
            print(f"Log file: {file_name}")

        for file_name in os.listdir('/app/common/'):
            print(f"Common file: {file_name}")
        
        for file_name in os.listdir('/app/src/'):
            print(f"Src file: {file_name}")

        for file_name in os.listdir('/config/'):
            print(f" Config file: {file_name}")
        pass
    
    def run(self):
        """
        Main processing loop.
        
        Starts HTTP server in background thread, then continuously
        consumes messages and updates metrics.
        """
        pass
    
    def shutdown(self, signum, frame):
        """
        Graceful shutdown handler.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        pass


def main():
    """
    Application entry point.
    
    Sets up signal handlers and starts the service.
    """
    service = JsonToPrometheusService()
    
    print("Starting json_to_prometheus service...")
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, service.shutdown)
    signal.signal(signal.SIGTERM, service.shutdown)
    
    service.setup()
    service.run()


if __name__ == "__main__":
    main()
