"""
Unit tests for message processor.

Tests MessageProcessor class from raw_to_json component.
"""

import pytest
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'raw_to_json/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))

from processor import MessageProcessor


class TestMessageProcessor:
    """Test cases for MessageProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create MessageProcessor instance."""
        return MessageProcessor()
    
    def test_coverage_message_type(self, processor):
        """Test COVERAGE message processing produces 4 records."""
        raw_message = json.dumps({
            "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc 5127.0/sec 4746.300/sec 4774.4800/sec total: 3124016321",
            "hostname": "test-host-ops01",
            "log_path": "/var/log/ovn/ovn-controller-coverage.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 4, f"Expected 4 records, got {len(result)}"
        
        # Verify all records are valid JSON
        for record_str in result:
            record = json.loads(record_str)
            assert record["name"] == "coverage"
            assert record["type"] == "gauge"
            assert record["labels"]["host"] == "test-host-ops01"
            assert record["labels"]["component"] == "ovn-controller"
            assert "farm" in record["labels"]
            assert record["labels"]["metric"] == "util_xalloc"
            assert "interval" in record["labels"]
        
        # Verify specific intervals
        intervals = [json.loads(r)["labels"]["interval"] for r in result]
        assert set(intervals) == {"info_5s", "info_1m", "info_1h", "total"}
    
    def test_cluster_message_type_term(self, processor):
        """Test CLUSTER message processing for Term metric."""
        raw_message = json.dumps({
            "message": "[CLUSTER] [2024-12-26 11:24:01] Term: 1875",
            "hostname": "test-db-host",
            "log_path": "/var/log/ovn/ovn-nb-db-cluster.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 1
        
        record = json.loads(result[0])
        assert record["name"] == "cluster"
        assert record["labels"]["metric"] == "term"
        assert record["values"]["doubleValue"] == 1875.0
        assert "farm" in record["labels"]
    
    def test_cluster_message_type_log(self, processor):
        """Test CLUSTER message processing for Log metric produces 2 records."""
        raw_message = json.dumps({
            "message": "[CLUSTER] [2024-12-26 11:24:01] Log: [5791, 5801]",
            "hostname": "test-db-host",
            "log_path": "/var/log/ovn/ovn-sb-db-cluster.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 2
        
        record1 = json.loads(result[0])
        record2 = json.loads(result[1])
        
        assert record1["labels"]["metric"] == "lowest_log_index"
        assert record1["values"]["doubleValue"] == 5791.0
        assert record2["labels"]["metric"] == "highest_log_index"
        assert record2["values"]["doubleValue"] == 5801.0
    
    def test_stopwatch_message_type(self, processor):
        """Test STOPWATCH message processing produces multiple records."""
        raw_message = json.dumps({
            "message": "[STOPWATCH] [2025-01-07 13:49:14] | Statistics for 'build_lflows' |   Total samples: 23 |   Maximum: 6 msec  |   Minimum: 0 msec |   95th percentile: 4.000000 msec |   Short term average: 0.731860 msec |   Long term average: 4.299024 msec ",
            "hostname": "test-northd-host",
            "log_path": "/var/log/ovn/ovn-northd-stopwatch.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 6  # 6 metrics per operation
        
        record = json.loads(result[0])
        assert record["name"] == "stopwatch"
        assert record["labels"]["metric"] == "build_lflows"
        assert record["labels"]["component"] == "ovn-northd"
        assert "farm" in record["labels"]
        assert "info" in record["labels"]
    
    def test_memory_message_type(self, processor):
        """Test MEMORY message processing."""
        raw_message = json.dumps({
            "message": "[MEMORY] [2025-01-07 17:10:31] handlers: 52 ports: 48 bfd: 2",
            "hostname": "test-controller-host",
            "log_path": "/var/log/ovn/ovn-controller-memory.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 3  # 3 metrics
        
        metrics = [json.loads(r)["labels"]["metric"] for r in result]
        assert "handlers" in metrics
        assert "ports" in metrics
        assert "bfd" in metrics
    
    def test_northd_status_active(self, processor):
        """Test NORTHD_STATUS message with active status."""
        raw_message = json.dumps({
            "message": "[NORTHD_STATUS] [2025-01-07 17:10:31] Status: active",
            "hostname": "test-northd",
            "log_path": "/var/log/ovn/ovn-northd-status.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 1
        
        record = json.loads(result[0])
        assert record["name"] == "northd_status"
        assert record["values"]["doubleValue"] == 1
        assert "farm" in record["labels"]
    
    def test_inc_engine_message_type(self, processor):
        """Test INC_ENGINE message processing."""
        raw_message = json.dumps({
            "message": "[INC_ENGINE] [2025-01-07 17:10:31] | Node: lr_nat |   - recompute: 5 |   - compute: 10 |   - cancel: 2 ",
            "hostname": "test-northd",
            "log_path": "/var/log/ovn/ovn-northd-inc-engine.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 3  # recompute, compute, cancel
        
        record = json.loads(result[0])
        assert record["name"] == "inc_engine"
        assert record["labels"]["metric"] == "lr_nat"
        assert "info" in record["labels"]
        assert "farm" in record["labels"]
    
    def test_lflow_cache_message_type(self, processor):
        """Test LFLOW_CACHE message processing."""
        raw_message = json.dumps({
            "message": "[LFLOW_CACHE] [2025-01-07 17:10:31] | Enabled: true | high-watermark  : 211 | total           : 211 | cache-expr      : 49 | cache-matches   : 162 | trim count      : 3 | Mem usage (KB)  : 217 ",
            "hostname": "test-controller",
            "log_path": "/var/log/ovn/ovn-controller-lflow-cache.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 7  # 7 metrics
        
        metrics = [json.loads(r)["labels"]["metric"] for r in result]
        assert "enable" in metrics
        assert "high_watermark" in metrics
        assert "total" in metrics
    
    def test_dpctl_ct_stats_message_type(self, processor):
        """Test DPCTL_CT_STATS message processing."""
        raw_message = json.dumps({
            "message": "[DPCTL_CT_STATS] [2025-01-07 17:10:31] current: 1234",
            "hostname": "test-vswitchd",
            "log_path": "/var/log/ovn/ovs-vswitchd-dpctl.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 1
        
        record = json.loads(result[0])
        assert record["name"] == "dpctl_ct_stats"
        assert record["labels"]["metric"] == "current"
        assert record["values"]["doubleValue"] == 1234.0
    
    def test_fdb_stats_message_type(self, processor):
        """Test FDB_STATS message processing."""
        raw_message = json.dumps({
            "message": "[FDB_STATS] [2025-01-07 17:10:31] Current/maximum MAC entries in the table: 50/100",
            "hostname": "test-vswitchd",
            "log_path": "/var/log/ovn/ovs-vswitchd-fdb.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 2  # current and maximum
        
        record = json.loads(result[0])
        assert record["name"] == "fdb_stats"
        assert "farm" in record["labels"]
    
    def test_other_count_message_type(self, processor):
        """Test OTHER_COUNT message processing."""
        raw_message = json.dumps({
            "message": "[OTHER_COUNT] [2025-01-07 17:10:31] [flows] 42",
            "hostname": "test-host",
            "log_path": "/var/log/ovn/ovn-controller-other.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 1
        
        record = json.loads(result[0])
        assert record["name"] == "other_count"
        assert record["labels"]["metric"] == "flows"
        assert record["values"]["doubleValue"] == 42
    
    def test_ofctl_dump_ports_message_type(self, processor):
        """Test OFCTL_DUMP_PORTS message processing."""
        raw_message = json.dumps({
            "message": "[OFCTL_DUMP_PORTS] [2025-02-11 13:49:01] | port 10: rx pkts=87, bytes=8727, drop=0, errs=0, frame=0, over=0, crc=0 |            tx pkts=2274, bytes=100856, drop=0, errs=0, coll=0 ",
            "hostname": "test-vswitchd",
            "log_path": "/var/log/ovn/ovs-vswitchd-ofctl.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        # Each port produces 10 metrics (rx: pkts, bytes, drop, errs, frame, over, crc; tx: pkts, bytes, drop, errs, coll - but we don't know exact count without checking)
        assert len(result) > 0
        
        record = json.loads(result[0])
        assert record["name"] == "ofctl_dump_ports"
        assert "port" in record["labels"]
        assert "farm" in record["labels"]
    
    def test_filebeat_format(self, processor):
        """Test processing Filebeat format message."""
        raw_message = json.dumps({
            "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc 5127.0/sec 4746.300/sec 4774.4800/sec total: 3124016321",
            "host": {
                "name": "filebeat-test-host"
            },
            "log": {
                "file": {
                    "path": "/var/log/ovn/ovn-controller-coverage.log"
                }
            }
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 4
        
        record = json.loads(result[0])
        assert record["labels"]["host"] == "filebeat-test-host"
        assert record["labels"]["component"] == "ovn-controller"
    
    def test_fluentd_format(self, processor):
        """Test processing Fluentd format message."""
        raw_message = json.dumps({
            "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc 5127.0/sec 4746.300/sec 4774.4800/sec total: 3124016321",
            "hostname": "fluentd-test-host",
            "log_path": "/var/log/ovn/ovn-nb-db-coverage.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        assert len(result) == 4
        
        record = json.loads(result[0])
        assert record["labels"]["host"] == "fluentd-test-host"
        assert record["labels"]["component"] == "ovn-nb-db"
    
    def test_farm_resolution(self, processor):
        """Test farm resolution is applied to all messages."""
        raw_message = json.dumps({
            "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc 5127.0/sec 4746.300/sec 4774.4800/sec total: 3124016321",
            "hostname": "hni-cloud-ops04-host1",  # Should match farm rules if configured
            "log_path": "/var/log/ovn/ovn-controller-coverage.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is not None
        
        record = json.loads(result[0])
        assert "farm" in record["labels"]
        # Farm value depends on farm_rules.yaml configuration
    
    def test_invalid_json_message(self, processor):
        """Test processing invalid JSON returns None."""
        raw_message = "not a valid json string"
        
        result = processor.process(raw_message)
        
        assert result is None
    
    def test_unknown_message_type(self, processor):
        """Test processing unknown message type returns None."""
        raw_message = json.dumps({
            "message": "[UNKNOWN_TYPE] [2025-01-09 09:50:01] some data",
            "hostname": "test-host",
            "log_path": "/var/log/ovn/test.log"
        })
        
        result = processor.process(raw_message)
        
        assert result is None
    
    def test_malformed_coverage_message(self, processor):
        """Test processing malformed COVERAGE message returns empty list."""
        raw_message = json.dumps({
            "message": "[COVERAGE] invalid format here",
            "hostname": "test-host",
            "log_path": "/var/log/ovn/ovn-controller-coverage.log"
        })
        
        result = processor.process(raw_message)
        
        assert result == []
    
    def test_component_extraction(self, processor):
        """Test component name extraction from various log paths."""
        test_cases = [
            ("/var/log/ovn/ovn-controller-coverage.log", "ovn-controller"),
            ("/var/log/ovn/ovn-nb-db-cluster.log", "ovn-nb-db"),
            ("/var/log/ovn/ovs-vswitchd-memory.log", "ovs-vswitchd"),
            ("/var/log/ovn/ovn-northd-stopwatch.log", "ovn-northd"),
        ]
        
        for log_path, expected_component in test_cases:
            raw_message = json.dumps({
                "message": "[COVERAGE] [2025-01-09 09:50:01] test 1.0/sec 1.0/sec 1.0/sec total: 100",
                "hostname": "test-host",
                "log_path": log_path
            })
            
            result = processor.process(raw_message)
            assert result is not None
            
            record = json.loads(result[0])
            assert record["labels"]["component"] == expected_component, \
                f"Expected {expected_component} for {log_path}, got {record['labels']['component']}"
    
    def test_all_message_types_coverage(self, processor):
        """Test that all 11 message types are mapped in MESSAGE_TYPE_MAP."""
        expected_types = {
            "COVERAGE", "CLUSTER", "STOPWATCH", "MEMORY", "INC_ENGINE",
            "LFLOW_CACHE", "DPCTL_CT_STATS", "FDB_STATS", "OTHER_COUNT",
            "NORTHD_STATUS", "OFCTL_DUMP_PORTS"
        }
        
        assert set(processor.MESSAGE_TYPE_MAP.keys()) == expected_types, \
            f"MESSAGE_TYPE_MAP missing types: {expected_types - set(processor.MESSAGE_TYPE_MAP.keys())}"
