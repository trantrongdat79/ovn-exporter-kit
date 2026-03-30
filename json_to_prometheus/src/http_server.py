"""
HTTP server for Prometheus metrics endpoint.

Serves metrics at /metrics endpoint for Prometheus scraping.
"""

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import CollectorRegistry, generate_latest
from threading import Thread

from common.logger import setup_logger


class MetricsHTTPServer:
    """
    HTTP server for exposing Prometheus metrics.
    
    Serves metrics at /metrics endpoint on configured port.
    """
    
    def __init__(self, registry: CollectorRegistry):
        """
        Initialize HTTP server.
        
        Args:
            registry: Prometheus registry to expose
        """
        self.logger = setup_logger(
            'json_to_prometheus-http',
            'logs/json_to_prometheus/http.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
        self.registry = registry
        self.port = int(os.getenv('PROMETHEUS_PORT', '8001'))
        self.server = None
        self.server_thread = None
    
    def start(self):
        """
        Start HTTP server in background thread.
        
        Serves metrics at http://0.0.0.0:<port>/metrics
        """
        pass
    
    def stop(self):
        """Stop HTTP server gracefully."""
        pass


class MetricsHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for /metrics endpoint.
    
    Handles GET requests and serves Prometheus-formatted metrics.
    """
    
    registry: CollectorRegistry = None
    
    def do_GET(self):
        """
        Handle GET request.
        
        Serves metrics at /metrics, returns 404 for other paths.
        """
        pass
    
    def log_message(self, format, *args):
        """Override to use custom logger instead of stderr."""
        pass
