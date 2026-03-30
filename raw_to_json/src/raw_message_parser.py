"""
Message parsing utilities for multiple input formats.

Handles parsing of raw metric messages from Filebeat and Fluentd
into normalized internal format.
"""

import json
import os
import re

from typing import Dict, Any, Optional
from common.logger import MyLogger

class MetricParser:
    """
    Base class for metric parsers.
    
    Defines interface for parsing different metric types.
    """
    def __init__(self, host: str, component: str, farm: str, msg: str):
        """
        Initialize parser with common parameters.
        
        Args:
            host: Hostname from the log source
            component: Component name (e.g., ovs-vswitchd, ovn-controller)
            farm: Farm identifier from farm resolver
            msg: Raw message string to parse
        """
        self.host = host
        self.component = component
        self.farm = farm
        self.msg = msg
        self.logger = MyLogger(
            'raw_to_json-raw-message-parser',
            'logs/raw_to_json/raw-message-parser.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
    
    def _create_metric_record(self, name: str, timestamp: str, metric: str, 
                             value: float, additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create standardized metric record.
        
        Args:
            name: Metric name (e.g., 'coverage', 'cluster')
            timestamp: Timestamp string
            metric: Metric identifier
            value: Numeric value for the metric
            additional_labels: Optional additional labels beyond host/component/farm/metric
            
        Returns:
            Dictionary representing a metric record
        """
        labels = {
            "host": self.host,
            "component": self.component,
            "farm": self.farm,
            "metric": metric
        }
        if additional_labels:
            labels.update(additional_labels)
        

        record = {
            "name": name,
            "type": "gauge",
            "time": timestamp,
            "labels": labels,
            "values": {
                "doubleValue": value
            }
        }

        self.logger.log_with_context(
            MyLogger.DEBUG,
            "Created metric record",
            record=record
        )
    
        return record
    
    def _serialize_records(self, records: list) -> list:
        """
        Convert records to JSON strings.
        
        Args:
            records: List of record dictionaries
            
        Returns:
            List of JSON strings
        """
        return [json.dumps(record) for record in records]
    
    def _validate_match(self, match, pattern_name: str = "") -> bool:
        """
        Validate regex match and log if invalid.
        
        Args:
            match: Regex match object
            pattern_name: Optional name for logging context
            
        Returns:
            True if match is valid, False otherwise
        """
        if not match:
            self.logger.log_with_context(
                MyLogger.WARNING,
                f"Failed to parse {pattern_name or 'message'}",
                message_preview=self.msg[:100]
            )
            return False
        return True
    
class CoverageMetricParser(MetricParser):
    '''
    Parser for OVN coverage metrics.
    
    Parses coverage statistics and creates separate metric records for different time intervals.
    Each input message produces 4 output records (5s, 1m, 1h, total).
    
    Args:
        host: Hostname from the log source
        component: Component name (e.g., ovs-vswitchd, ovn-controller)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    INPUT: "[COVERAGE] [2024-12-26 11:24:01] poll_create_node 4.0/sec 3.933/sec 4.0353/sec total: 2966669"
    OUTPUT: List of 4 JSON strings with labels including host, component, farm, metric, interval
    '''
    # Pre-compiled regex pattern for performance
    PATTERN = re.compile(r"\[COVERAGE\] \[(.*?)\] (\S+)\s+(\d+\.\d+)/sec\s+(\d+\.\d+)/sec\s+(\d+\.\d+)/sec\s+total: (\d+)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "COVERAGE"):
            return []

        timestamp = match.group(1)
        metric_name = match.group(2)
        info_5s = float(match.group(3))
        info_1m = float(match.group(4))
        info_1h = float(match.group(5))
        info_total = int(match.group(6))

        records = [
            self._create_metric_record("coverage", timestamp, metric_name, info_5s, {"interval": "info_5s"}),
            self._create_metric_record("coverage", timestamp, metric_name, info_1m, {"interval": "info_1m"}),
            self._create_metric_record("coverage", timestamp, metric_name, info_1h, {"interval": "info_1h"}),
            self._create_metric_record("coverage", timestamp, metric_name, info_total, {"interval": "total"})
        ]

        return self._serialize_records(records)

class ClusterMetricParser(MetricParser):
    '''
    Parser for OVN cluster status metrics.
    
    Parses OVN database cluster metrics including term, log indices, election timer,
    uncommitted/unapplied entries, and disconnections.
    
    Args:
        host: Hostname from the log source
        component: Component name (e.g., ovn-nb-db, ovn-sb-db)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    INPUT: [CLUSTER] [2024-12-26 11:24:01] Term: 1875
    OUTPUT: JSON string with labels including host, component, farm, metric
    '''
    # Pre-compiled regex pattern for performance
    PATTERN = re.compile(r"\[CLUSTER\] \[(.*?)\] (.*): (.*)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "CLUSTER"):
            return []
        
        timestamp = match.group(1)
        metric_name = match.group(2)
        value = match.group(3)
        records = []
        
        # Simple single-value metrics
        if metric_name in ["Term", "Election timer", "Entries not yet committed", 
                           "Entries not yet applied", "Disconnections"]:
            normalized_metric = metric_name.lower().replace(" ", "_")
            records = [self._create_metric_record("cluster", timestamp, normalized_metric, float(value))]
            
        elif metric_name == "Log":
            strip_log_index = value.strip("[]").split(", ")
            records = [
                self._create_metric_record("cluster", timestamp, "lowest_log_index", float(strip_log_index[0])),
                self._create_metric_record("cluster", timestamp, "highest_log_index", float(strip_log_index[1]))
            ]
        
        return self._serialize_records(records)

class StopwatchMetricParser(MetricParser):
    # Pre-compiled regex patterns for performance
    TIMESTAMP_PATTERN = re.compile(r'\[STOPWATCH\]\s*\[(.*?)\]')
    METRIC_PATTERN = re.compile(
        r'\|\s*Statistics for \'(\S*)\'\s*'
        r'\|\s*Total samples: (\d*)\s*'
        r'\|\s*Maximum: (\d*) msec \s*'
        r'\|\s*Minimum: (\d*) msec\s*'
        r'\|\s*95th percentile: (\d*.\d*) msec\s*'
        r'\|\s*Short term average: (\d*.\d*) msec\s*'
        r'\|\s*Long term average: (\d*.\d*) msec\s*'
    )
    TIMESTAMP_PREFIX_LEN = len("[STOPWATCH] [YYYY-MM-DD HH:MM:SS]")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        '''
        Parse OVN stopwatch performance metrics.
        
        Extracts timing statistics for various OVN operations including samples, max/min,
        percentiles, and averages. Each operation produces 6 metric records.
        
        Returns:
            List of JSON strings with labels: host, component, farm, metric, info
        '''
        "| Statistics for 'build_lflows' |   Total samples: 23 |   Maximum: 6 msec |   Minimum: 0 msec |   95th percentile: 4.000000 msec |   Short term average: 0.731860 msec |   Long term average: 4.299024 msec "
        
        records = []
        timestamp_match = self.TIMESTAMP_PATTERN.search(self.msg)
        timestamp = timestamp_match.group(1)
        matches = self.METRIC_PATTERN.findall(self.msg[self.TIMESTAMP_PREFIX_LEN:])
        for metric, total_samples, maximum, minimum, percentile_95th, short_term_average, long_term_average in matches:
        #for metric in matches:
            record = [
                self._create_metric_record("stopwatch", timestamp, metric, float(total_samples), {"info": "total_samples"}),
                self._create_metric_record("stopwatch", timestamp, metric, float(maximum), {"info": "maximum"}),
                self._create_metric_record("stopwatch", timestamp, metric, float(minimum), {"info": "minimum"}),
                self._create_metric_record("stopwatch", timestamp, metric, float(percentile_95th), {"info": "percentile_95th"}),
                self._create_metric_record("stopwatch", timestamp, metric, float(short_term_average), {"info": "short_term_average"}),
                self._create_metric_record("stopwatch", timestamp, metric, float(long_term_average), {"info": "long_term_average"})
            ]
            records = records + record
        # Return records as JSON strings
        return self._serialize_records(records)

class MemoryMetricParser(MetricParser):
    """
    Parser for OVN memory usage metrics.
    
    Parses memory statistics for various OVN components and data structures.
    
    Args:
        host: Hostname from the log source
        component: Component name (e.g., ovn-northd, ovn-controller)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        List of JSON strings with labels: host, component, farm, metric
    """
    # Pre-compiled regex patterns for performance
    TIMESTAMP_PATTERN = re.compile(r'\[MEMORY\]\s*\[(.*?)\]')
    METRIC_PATTERN = re.compile(r'(\w[\w-]*):\s*(\d+)')
    TIMESTAMP_PREFIX_LEN = len("[MEMORY] [YYYY-MM-DD HH:MM:SS]")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        # Initialize a list to hold the JSON objects
        records = []

        # Extract the timestamp from the message
        timestamp_match = self.TIMESTAMP_PATTERN.search(self.msg)
        timestamp = timestamp_match.group(1)

        # Extract all metrics (metric, value)
        matches = self.METRIC_PATTERN.findall(self.msg[self.TIMESTAMP_PREFIX_LEN:])

        # Build a JSON record for each metric found
        for metric, value in matches:
            record = self._create_metric_record("memory", timestamp, metric, int(value))
            records.append(record)

        # Return the list of records as a list of JSON strings (one string per metric)
        return self._serialize_records(records)

class NorthdStatusMetricParser(MetricParser):
    """
    Parser for OVN northd daemon status.
    
    Maps northd status strings to numeric values: active=1, standby=0.5, paused=-1, other=0.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovn-northd)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        JSON string with labels: host, component, farm
    """
    # Pre-compiled regex pattern for performance
    PATTERN = re.compile(r"\[NORTHD_STATUS\] \[(.*?)\] Status: (\S+)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)
    
    def parse(self):
        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "NORTHD_STATUS"):
            return[] #return an empty list if format is invalid
        
        # Extracting values:
        timestamp = match.group(1)
        northd_status = match.group(2)
        
        # Map status to numeric value
        if northd_status == "active":
            value = 1
        elif northd_status == "standby":
            value = 0.5
        elif northd_status == "paused":
            value = -1
        else:
            value = 0
        
        # Note: Using empty string for metric since original doesn't have metric in labels
        record = self._create_metric_record("northd_status", timestamp, "", value)
        # Remove the metric key since original doesn't have it
        del record["labels"]["metric"]
        
        records = [record]
        return self._serialize_records(records)

class IncEngineMetricParser(MetricParser):
    """
    Parser for OVN incremental processing engine metrics.
    
    Tracks recompute, compute, and cancel operations for each engine node.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovn-northd)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        List of JSON strings with labels: host, component, farm, metric, info
    """
    # Pre-compiled regex patterns for performance
    TIMESTAMP_PATTERN = re.compile(r'\[INC_ENGINE\]\s*\[(.*?)\]')
    METRIC_PATTERN = re.compile(
        r'\|\s*Node:\s*(\S*)\s*'
        r'\|\s*\-\s*recompute:\s*(\d*)\s*'
        r'\|\s*\-\s*compute:\s*(\d*)\s*'
        r'\|\s*\-\s*cancel:\s*(\d*)\s*'
    )
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        records = []
        timestamp_match = self.TIMESTAMP_PATTERN.search(self.msg)
        timestamp = timestamp_match.group(1)
        matches = self.METRIC_PATTERN.findall(self.msg)
        for metric, recompute, compute, cancel in matches:
            record = [
                self._create_metric_record("inc_engine", timestamp, metric, int(recompute), {"info": "recompute"}),
                self._create_metric_record("inc_engine", timestamp, metric, int(compute), {"info": "compute"}),
                self._create_metric_record("inc_engine", timestamp, metric, int(cancel), {"info": "cancel"})
            ]
            records += record

        # Return records as JSON strings
        return self._serialize_records(records)
    
class LflowCacheMetricParser(MetricParser):
    """
    Parser for OVN logical flow cache statistics.
    
    Tracks cache status, watermarks, cache hits/misses, and memory usage.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovn-controller)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        List of JSON strings with labels: host, component, farm, metric
    """
    # Pre-compiled regex pattern for performance
    METRIC_PATTERN = re.compile(
        r'\[LFLOW_CACHE\]\s*\[(.*?)\]\s*'
        r'\|\s*Enabled\s*:\s*(\S*)\s*'
        r'\|\s*high-watermark\s*:\s*(\d*)\s*'
        r'\|\s*total\s*:\s*(\d*)\s*'
        r'\|\s*cache-expr\s*:\s*(\d*)\s*'
        r'\|\s*cache-matches\s*:\s*(\d*)\s*'
        r'\|\s*trim count\s*:\s*(\d*)\s*'
        r'\|\s*Mem usage \(KB\)\s*:\s*(\d*)\s*'
    )
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        records = []
        """[LFLOW_CACHE] [2025-01-07 17:10:31] | Enabled: true | high-watermark  : 211 | total           : 211 
        | cache-expr      : 49 | cache-matches   : 162 | trim count      : 3 | Mem usage (KB)  : 217
        """
        match = self.METRIC_PATTERN.match(self.msg)
        if not self._validate_match(match, "LFLOW_CACHE"):
            return [] #return an empty list if format is invalid
        
        timestamp = match.group(1)
        enable = match.group(2)
        high_watermark = match.group(3)
        total = match.group(4)
        cache_expr = match.group(5)
        cache_matches = match.group(6)
        trim_count = match.group(7)
        mem_usage = match.group(8)
        if enable == "true":
            enable_to_number = 1
        else:
            enable_to_number = 0
        records = [
            self._create_metric_record("lflow_cache", timestamp, "enable", int(enable_to_number)),
            self._create_metric_record("lflow_cache", timestamp, "high_watermark", int(high_watermark)),
            self._create_metric_record("lflow_cache", timestamp, "total", int(total)),
            self._create_metric_record("lflow_cache", timestamp, "cache_expr", int(cache_expr)),
            self._create_metric_record("lflow_cache", timestamp, "cache_matches", int(cache_matches)),
            self._create_metric_record("lflow_cache", timestamp, "trim_count", int(trim_count)),
            self._create_metric_record("lflow_cache", timestamp, "mem_usage", int(mem_usage))
        ]
        # Return records as JSON strings
        return self._serialize_records(records)

class DpctlCtStatsMetricParser(MetricParser):
    """
    Parser for OVS datapath connection tracking statistics.
    
    Parses dpctl conntrack statistics from OVS.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovs-vswitchd)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        JSON string with labels: host, component, farm, metric
    """
    # Pre-compiled regex pattern for performance
    PATTERN = re.compile(r"\[DPCTL_CT_STATS\]\s*\[(.*?)\]\s*(\S*):\s*(\d*)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "DPCTL_CT_STATS"):
            return []
        
        timestamp = match.group(1)
        metric = match.group(2)
        value = match.group(3)

        record = self._create_metric_record("dpctl_ct_stats", timestamp, metric, float(value))
        return self._serialize_records([record])

class FdbStatsMetricParser(MetricParser):
    """
    Parser for OVS forwarding database (FDB) statistics.
    
    Tracks MAC address table usage and statistics.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovs-vswitchd)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        List of JSON strings with labels: host, component, farm, metric
    """
    # Pre-compiled regex patterns for performance
    PATTERN = re.compile(r"\[FDB_STATS\]\s*\[(.*?)\]\s*(.*):\s*(\S*)")
    SMALL_PATTERN = re.compile(r"(\d*)\/(\d*)")
    METRIC_PATTERN = re.compile(r"(.* MAC entries)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        records = []

        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "FDB_STATS"):
            return []
        
        timestamp = match.group(1)
        msg_type = match.group(2)
        value = match.group(3)
        if msg_type == "Current/maximum MAC entries in the table":
            small_match = self.SMALL_PATTERN.match(value)

            current_value = small_match.group(1)
            maximum_value = small_match.group(2)
            records = [
                self._create_metric_record("fdb_stats", timestamp, "current_mac_entries", int(current_value)),
                self._create_metric_record("fdb_stats", timestamp, "maximum_mac_entries", int(maximum_value))
            ]
        elif msg_type == "Current static MAC entries in the table ":
            records = [
                self._create_metric_record("fdb_stats", timestamp, "static_mac_entries", int(value))
            ]
        elif msg_type[:len("Total number of ")] == "Total number of ":
            small_match = self.METRIC_PATTERN.match(msg_type[len("Total number of "):])
            metric = small_match.group(1).lower().replace(" ","_")
            records = [
                self._create_metric_record("fdb_stats", timestamp, metric, int(value))
            ]
        else:
            return []
                
        # Return records as JSON strings
        return self._serialize_records(records)

class OtherCountMetricParser(MetricParser):
    """
    Parser for miscellaneous OVN counter metrics.
    
    Generic parser for various count-based metrics.
    
    Args:
        host: Hostname from the log source
        component: Component name
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        JSON string with labels: host, component, farm, metric
    """
    # Pre-compiled regex pattern for performance
    PATTERN = re.compile(r"\[OTHER_COUNT\]\s*\[(.*?)\]\s*\[(\S*?)\]\s*(\d*)")
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        match = self.PATTERN.match(self.msg)
        if not self._validate_match(match, "OTHER_COUNT"):
            return []

        timestamp = match.group(1)
        metric = match.group(2)
        value = match.group(3)

        record = self._create_metric_record("other_count", timestamp, metric, int(value))
        return self._serialize_records([record])

class OfctlDumpPortsMetricParser(MetricParser):
    """
    Parser for OpenFlow port statistics.
    
    Parses ofctl dump-ports output including rx/tx packets, bytes, drops, errors.
    
    Args:
        host: Hostname from the log source
        component: Component name (ovs-vswitchd)
        farm: Farm identifier resolved from hostname
        msg: Raw message string to parse
    
    Returns:
        List of JSON strings with labels: host, component, farm, metric, port, direction
    """
    # Pre-compiled regex patterns for performance
    TIMESTAMP_PATTERN = re.compile(r'\[OFCTL_DUMP_PORTS\] \[(.*?)\]')
    METRIC_PATTERN = re.compile(
        r'port\s*(\S*):\s*rx pkts=(\S*), bytes=(\S*), drop=(\S*), errs=(\S*), frame=(\S*), over=(\S*), crc=(\S*)\s*\|\s*tx pkts=(\S*), bytes=(\S*), drop=(\S*), errs=(\S*), coll=(\S*)\s*'
    )
    
    def __init__(self, host, component, farm, msg):
        super().__init__(host, component, farm, msg)

    def parse(self):
        '''
        INPUT:
        [OFCTL_DUMP_PORTS] [2025-02-11 13:49:01] | OFPST_PORT reply (xid=0x2): 7 ports |   port  4: rx pkts=0, bytes=0, drop=?, errs=?, frame=?, over=?, crc=? |            tx pkts=0, bytes=0, drop=?, errs=?, coll=? |   port  1: rx pkts=0, bytes=0, drop=?, errs=?, frame=?, over=?, crc=? |            tx pkts=0, bytes=0, drop=?, errs=?, coll=? |   port LOCAL: rx pkts=0, bytes=0, drop=0, errs=0, frame=0, over=0, crc=0 |            tx pkts=0, bytes=0, drop=0, errs=0, coll=0 |   port 10: rx pkts=87, bytes=8727, drop=0, errs=0, frame=0, over=0, crc=0 |            tx pkts=2274, bytes=100856, drop=0, errs=0, coll=0 |   port  2: rx pkts=0, bytes=0, drop=?, errs=?, frame=?, over=?, crc=? |            tx pkts=2114, bytes=88788, drop=?, errs=?, coll=? |   port  9: rx pkts=75945, bytes=7321778, drop=0, errs=0, frame=0, over=0, crc=0 |            tx pkts=75942, bytes=7322823, drop=0, errs=0, coll=0 |   port  3: rx pkts=74971, bytes=7229166, drop=?, errs=?, frame=?, over=?, crc=? |            tx pkts=74978, bytes=7229460, drop=?, errs=?, coll=?
        
        '''
        records = []
        timestamp_match = self.TIMESTAMP_PATTERN.search(self.msg)
        timestamp = timestamp_match.group(1)

        matches = self.METRIC_PATTERN.findall(self.msg)

        # Helper to parse numeric fields (treat "?" as 0)
        def parse_value(val):
            if val == '?':
                return -1
            try:
                return float(val)
            except:
                return -1
            
        for (port, 
             rx_pkts, rx_bytes, rx_drop, rx_errs, rx_frame, rx_over, rx_crc, 
             tx_pkts, tx_bytes, tx_drop, tx_errs, tx_coll) in matches:

            # Build a dictionary of the extracted fields so we can loop easily
            values_dict = {
                'rx_pkts':  rx_pkts,
                'rx_bytes': rx_bytes,
                'rx_drop':  rx_drop,
                'rx_errs':  rx_errs,
                'rx_frame': rx_frame,
                'rx_over':  rx_over,
                'rx_crc':   rx_crc,
                'tx_pkts':  tx_pkts,
                'tx_bytes': tx_bytes,
                'tx_drop':  tx_drop,
                'tx_errs':  tx_errs,
                'tx_coll':  tx_coll
            }

            for metric_key, raw_val in values_dict.items():
                numeric_val = parse_value(raw_val)
                record = [
                    self._create_metric_record("ofctl_dump_ports", timestamp, metric_key, numeric_val, {"port": port})
                ]
                records += record
                
        # Return records as JSON strings
        return self._serialize_records(records)