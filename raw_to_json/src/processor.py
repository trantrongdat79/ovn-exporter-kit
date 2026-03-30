"""
Message transformation logic for raw_to_json component.

Processes raw metric messages and transforms them into structured JSON format.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional

from common.logger import MyLogger
from raw_message_parser import *
from farm_resolver import FarmResolver


class MessageProcessor:
    """
    Processor for transforming raw metrics into structured JSON messages.
    
    Handles parsing, farm resolution, and metric splitting.
    """
    
    def __init__(self):
        """Initialize processor with parsers and resolvers."""
        self.logger = MyLogger(
            'raw_to_json-processor',
            'logs/raw_to_json/processor.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
        self.farm_resolver = FarmResolver()

        self.MESSAGE_TYPE_MAP = {
            "COVERAGE": CoverageMetricParser,
            "CLUSTER": ClusterMetricParser,
            "STOPWATCH": StopwatchMetricParser,
            "MEMORY": MemoryMetricParser,
            "INC_ENGINE": IncEngineMetricParser,
            "LFLOW_CACHE": LflowCacheMetricParser,
            "DPCTL_CT_STATS": DpctlCtStatsMetricParser,
            "FDB_STATS": FdbStatsMetricParser,
            "OTHER_COUNT": OtherCountMetricParser,
            "NORTHD_STATUS": NorthdStatusMetricParser,
            "OFCTL_DUMP_PORTS": OfctlDumpPortsMetricParser,
        }

        self.message_type_parser_pattern = r"\[(.*?)\]"
    
    def process(self, raw_message: str) -> Optional[List[str]]:
        """
        Process raw message into list of structured metric messages.
        
        One input message produces multiple output messages.
        
        Args:
            raw_message: Raw message value from Kafka (JSON string)
            
        Returns:
            List of JSON strings, each representing a metric, or None if processing fails
            [
                {"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "site2-osp-network-03-2024.2-120", "component": "ovs-vswitchd", "metric": "util_xalloc", "interval": "info_5s"}, "values": {"doubleValue": 1278.2}}
                {"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "site2-osp-network-03-2024.2-120", "component": "ovs-vswitchd", "metric": "util_xalloc", "interval": "info_1m"}, "values": {"doubleValue": 2199.633}}
                {"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "site2-osp-network-03-2024.2-120", "component": "ovs-vswitchd", "metric": "util_xalloc", "interval": "info_1h"}, "values": {"doubleValue": 2187.2597}}
                {"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "site2-osp-network-03-2024.2-120", "component": "ovs-vswitchd", "metric": "util_xalloc", "interval": "total"}, "values": {"doubleValue": 19171811967}}
            ]
        """
        msg = self._parse_raw_message(raw_message)
        
        if not msg:
            return None
        
        # Process message based on its type
        message_class = self.MESSAGE_TYPE_MAP.get(msg.get("message_class"))

        if message_class:
            hostname = msg.get("hostname")
            component = msg.get("component")
            farm = msg.get("farm")
            message = msg.get("message")
            
            try:
                return message_class(hostname, component, farm, message).parse()
            except Exception as e:
                self.logger.log_with_context(
                    MyLogger.ERROR,
                    "Failed to parse message",
                    error=str(e),
                    message_class=msg.get("message_class"),
                    raw_message=raw_message[:200]  # Log first 200 chars
                )
                return None
        
        return None
            
    def _parse_raw_message(self, raw_message: str) -> Optional[Dict[str, Any]]:
        """
        Parse raw message and extract fields.
        
        Args:
            raw_message: Raw Kafka message (JSON string)
            {
                "log": {
                    "file": { "path": "/var/log/ovn-monitoring/ovn-controller-coverage.log" },
                    "offset": 3287177
                },
                "message": "[COVERAGE] [2026-02-05 16:16:02] txn_unchanged              0.4/sec     0.867/sec        0.9272/sec   total: 3331757",
                "host": { "name": "Openstack-compute-2-ovn-scale-test" }
            }

        Returns:
            Message dict with: message, hostname, component, message type, farm
        """

        try:
            message_data = json.loads(raw_message)
            
            # Extract hostname
            if message_data.get("hostname", "Unknown") == "Unknown":
                hostname = message_data.get("host", {}).get("name", "Unknown")
            else:
                hostname = message_data.get("hostname")

            # Extract farm info
            message_farm = self.farm_resolver.resolve(hostname)

            # Extract component
            if message_data.get("log_path", "Unknown") == "Unknown":
                log_path = message_data.get("log", {}).get("file",{}).get("path", "Unknown")
            else:
                log_path = message_data.get("log_path")

            component = self.extract_component(log_path)

            # Extract message
            message = message_data.get("message")

            message_class = self.extract_message_class(message)

        except json.JSONDecodeError as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Failed to decode raw message as JSON",
                error=str(e),
                raw_message=raw_message
            )
            return None

        except Exception as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Failed to extract fields from raw message",
                error=str(e),
                raw_message=raw_message
            )
            return None

        return {
            "message": message,
            "hostname": hostname,
            "component": component,
            "message_class": message_class,
            "farm": message_farm
        }

    def extract_component(self, file_path: str) -> Optional[str]:
        """
        Extract component name from log file path.
        
        Args: 
            file_path (str): The path to the log file.
        Returns:
            Optional[str]: The extracted component name or None if not found.
        """
        # Extract the filename from the path
        file_name = file_path.split("/")[-1]
        
        # Find the last hyphen and truncate the part before ".log"
        last_hyphen_index = file_name.rfind("-")
        if last_hyphen_index != -1:
            return file_name[:last_hyphen_index]
        return None
    
    def extract_message_class(self, message: str) -> Optional[str]:
        """
        Parse message class from raw message string.
        
        Args:
            message (str): The raw message string.
        Returns:
            Optional[str]: The extracted message class or None if not found.
        """
        match = re.match(self.message_type_parser_pattern, message)
        if not match:
            return None
        return match.group(1)