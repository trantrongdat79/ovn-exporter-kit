# OVN Exporter Kit

A containerized Kafka-based data pipeline for collecting, processing, and exporting OVN (Open Virtual Network) metrics to Prometheus. This kit transforms raw metric logs into structured JSON format and exposes them via Prometheus client for monitoring and visualization.

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Components](#2-components)
  - [1. ovn-metric-raw_to_json](#1-ovn-metric-raw_to_json)
  - [2. ovn-metric-json_to_prometheus](#2-ovn-metric-json_to_prometheus)
- [3. Development Guide](#3-development-guide)
  - [1. Project Structure](#1-project-structure)
  - [2. Code Style](#2-code-style)
- [4. Design Decisions & Constraints](#4-design-decisions--constraints)
- [5. Architecture](#5-architecture)
- [6. Deployment](#6-deployment)
- [7. Configuration](#7-config-guide)

---

## 1. Overview

### Problem Statement
OVN infrastructure generates coverage metrics that need to be monitored and visualized. These metrics are collected via cron jobs and exported to Kafka in raw format by tools like Filebeat or Fluentd. A processing pipeline is required to transform these raw metrics into structured formats suitable for time-series databases like Prometheus.

### Solution
The OVN Exporter Kit provides a two-stage pipeline:

1. **Stage 1 (raw_to_json)**: Consumes raw metric messages from Kafka, parses and normalizes them, extracts metadata (host, farm, component), and publishes structured JSON metrics back to Kafka.

2. **Stage 2 (json_to_prometheus)**: Consumes structured JSON metrics from Kafka and exposes them via a Prometheus-compatible HTTP endpoint for scraping.

### Key Features
- **Scalable**: Stateless design allows horizontal scaling of consumers
- **Containerized**: Docker-based deployment for easy orchestration
- **Flexible Configuration**: Environment variables for runtime config, YAML for business logic
- **Multi-format Support**: Handles different input message formats from various log shippers
- **Farm-aware**: Automatically enriches metrics with farm information based on hostname patterns

### Data Flow
```
OVN Servers → Cron Jobs → Filebeat/Fluentd → Kafka (ovn-metrics-raw)
                                                      ↓
                                          [ovn-metric-raw_to_json]
                                                      ↓
                                             Kafka (ovn-metrics-json)
                                                      ↓
                                        [ovn-metric-json_to_prometheus]
                                                      ↓
                                          Prometheus HTTP Endpoint (Port 8001)
                                                      ↓
                                              Grafana Dashboards
```
---

## 2. Components
### 1. ovn-metric-raw_to_json

**Purpose**: Kafka consumer that transforms raw OVN metric messages into structured JSON format.

**Input**: Kafka topic `ovn-metrics-raw` - Raw metrics collected by cron jobs and shipped via Filebeat/Fluentd  
#### Input Format

**Format 1** (Filebeat with nested structure):
```json
{
  "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc              5127.0/sec  4746.300/sec     4774.4800/sec   total: 3124016321",
  "host": {
    "name": "host1"
  },
  "log": {
    "file": {
      "path": "/home/admin/log/openvswitch/ovn-nb-db-coverage.log"
    }
  }
}
```

**Format 2** (Fluentd with flat structure):
```json
{
  "message": "[COVERAGE] [2025-01-09 09:50:01] util_xalloc              5127.0/sec  4746.300/sec     4774.4800/sec   total: 3124016321",
  "log_path": "/home/admin/log/openvswitch/ovn-nb-db-coverage.log",
  "hostname": "host1"
}
```

#### Output Format

Each input message is transformed into **separate messages** for each metric the message contain. 
For example: This input message contains 4 metrics hence 4 output messages:
- Input:
```

[COVERAGE] [2025-01-09 09:50:01]util_xalloc              5127.0/sec  4746.300/sec     4774.4800/sec   total: 3124016321
```
- Output: 
```

{"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "host1", "component": "ovn-nb-db", "metric": "util_xalloc", "interval": "info_5s"}, "values": {"doubleValue": 5127.0}}
{"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "host1", "component": "ovn-nb-db", "metric": "util_xalloc", "interval": "info_1m"}, "values": {"doubleValue": 4746.300}}
{"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "host1", "component": "ovn-nb-db", "metric": "util_xalloc", "interval": "info_1h"}, "values": {"doubleValue": 4774.4800}}
{"name": "coverage", "type": "gauge", "time": "2026-02-03 15:41:01", "labels": {"host": "host1", "component": "ovn-nb-db", "metric": "util_xalloc", "interval": "total"}, "values": {"doubleValue": 3124016321}}

```
### 2. ovn-metric-json_to_prometheus

**Purpose**: Kafka consumer that exposes JSON metrics via Prometheus HTTP endpoint.

**Input**: Kafka topic `ovn-metrics-json` - Structured JSON metrics from raw_to_json component  
**Output**: Prometheus client HTTP endpoint on port `8001` with full metrics and lables, refresh every 1 minutes
```

coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_5s",metric="util_xalloc"} 5127.0
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_1m",metric="util_xalloc"} 4746.300
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_1h",metric="util_xalloc"} 4774.4800
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="total",metric="util_xalloc"} 3124016321
```

---

## 3. Development Guide

### 1. Project Structure

The project follows a monorepo structure with clear separation between components, shared utilities, and configuration.

```
ovn-exporter-kit/
├── common/                          # Shared utilities and libraries
│   ├── __init__.py
│   ├── kafka_client.py             # Kafka producer/consumer wrappers
│   ├── json_message_schemas.py     # JSON message schemas/validators
│   ├── logger.py                   # JSON structured logging setup
│   └── config_loader.py            # Configuration file loader (YAML)
│
├── raw_to_json/                     # Component 1: Raw metrics processor
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # Entry point
│   │   ├── consumer.py             # Kafka consumer logic
│   │   ├── processor.py            # Message transformation logic
│   │   ├── producer.py             # Kafka producer logic
│   │   ├── raw_message_parser.py   # Input message format parsers
│   │   └── farm_resolver.py        # Farm assignment logic
│   ├── Dockerfile                  # Container build instructions
│   ├── requirements.txt            # Python dependencies
│   └── .dockerignore
│
├── json_to_prometheus/              # Component 2: Prometheus exporter
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # Entry point
│   │   ├── consumer.py             # Kafka consumer logic
│   │   ├── exporter.py             # Prometheus metrics registry
│   │   └── http_server.py          # HTTP endpoint handler
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── config/                          # Configuration files
│   ├── farm_rules.yaml             # Farm assignment rules
│   └── farm_rules.example.yaml     # Example template
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── unit/                       # Unit tests
│   │   ├── test_message_parser.py
│   │   ├── test_farm_resolver.py
│   │   ├── test_processor.py
│   │   └── test_exporter.py
│   ├── integration/                # Integration tests (future)
│   │   └── test_pipeline.py
│   └── fixtures/                   # Test data and fixtures
│       ├── sample_messages.json
│       └── test_farm_rules.yaml
│
├── logs/                            # Log file output directory (gitignored)
│   ├── raw_to_json/
│   └── json_to_prometheus/
│
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Environment template
├── docker-compose.yml               # Multi-container orchestration
├── requirements-dev.txt             # Development dependencies (black, pytest, etc.)
├── .gitignore
├── .dockerignore
├── pyproject.toml                   # Black/tool configuration
└── README.md
```

#### Directory Purpose Breakdown

**`common/`** - Shared Business Logic
- Eliminates code duplication between components
- Houses shared utilities (Kafka clients, JSON schemas, logging)
- Can be imported by both components: `from common.kafka_client import KafkaConsumerWrapper`

**`raw_to_json/` & `json_to_prometheus/`** - Component Isolation
- Each component is independently deployable
- Separate Docker images for granular scaling
- Own dependency management via `requirements.txt`
- Clear entry points (`main.py`) for container execution
- Component-specific logic stays within component directory

**`raw_to_json/src/`** - Raw Metrics Processing Pipeline
- **`main.py`**: Application entry point
  - Initializes logger, consumer, processor, and producer
  - Orchestrates main processing loop
  - Handles graceful shutdown via signal handlers (SIGINT, SIGTERM)
  - Coordinates component lifecycle
  
- **`consumer.py`**: Kafka Consumer Management
  - Wraps Kafka consumer with configuration
  - Generates dynamic consumer group names (with date+hour suffix)
  - Polls messages from `ovn-metrics-raw` topic
  - Handles offset commits and connection management
  
- **`processor.py`**: Message Transformation Engine
  - Core business logic for message processing
  - Coordinates parsing, farm resolution, and metric splitting
  - Takes 1 input message → produces 4 output messages (per time interval)
  - Integrates `raw_message_parser` and `farm_resolver`
  
- **`producer.py`**: Kafka Producer Management
  - Wraps Kafka producer with configuration
  - Publishes JSON messages to `ovn-metrics-json` topic
  - Manages producer flush and cleanup
  
- **`raw_message_parser.py`**: Input Format Handler
  - Parses both Filebeat (nested) and Fluentd (flat) JSON formats
  - Extracts: message text, hostname, log path
  - Parses coverage metric lines with regex
  - Extracts component name from log file path
  - Returns normalized data structures
  
- **`farm_resolver.py`**: Farm Assignment Logic
  - Loads farm rules from `/config/farm_rules.yaml`
  - Pattern-matches hostnames to farm identifiers
  - Sequential rule checking (first match wins)
  - Falls back to "other" farm for unmatched hosts

**`json_to_prometheus/src/`** - Prometheus Metrics Exporter
- **`main.py`**: Application entry point
  - Initializes logger, consumer, exporter, and HTTP server
  - Starts HTTP server in background thread
  - Runs consumer loop to update metrics continuously
  - Handles graceful shutdown for both consumer and HTTP server
  
- **`consumer.py`**: Kafka Consumer Management
  - Consumes JSON messages from `ovn-metrics-json` topic
  - Deserializes JSON to MetricMessage objects
  - Generates consumer group with date+hour suffix
  - Handles message polling and offset management
  
- **`exporter.py`**: Prometheus Metrics Registry
  - Maintains in-memory Prometheus gauge metrics
  - Creates metrics with labels: component, host, farm, interval, metric
  - Updates metric values as messages arrive
  - Manages metric lifecycle and expiration (1-minute refresh)
  - Provides registry for HTTP server
  
- **`http_server.py`**: HTTP Endpoint Handler
  - Serves metrics at `/metrics` endpoint on port 8001
  - Implements HTTP request handler for Prometheus scraping
  - Runs in background thread
  - Returns Prometheus exposition format
  - Handles graceful shutdown

**`config/`** - Configuration Management
- Version-controlled farm rules
- Example files guide new deployments
- Mounted as volume in containers for hot-reloading

**`tests/`** - Comprehensive Testing
- Unit tests validate individual functions in isolation
- Integration tests (future) validate end-to-end pipeline
- Fixtures provide reusable test data

**`logs/`** - Runtime Logs
- Gitignored directory for local development logs
- In production, logs written to container stdout/stderr
- Structured for log aggregation systems

#### Key Design Principles

1. **Separation of Concerns**: Components don't import from each other, only from `common/`
2. **Single Responsibility**: Each module has one clear purpose
3. **Testability**: Business logic separated from infrastructure (Kafka, HTTP)
4. **Docker-First**: Each component builds independently
5. **Configuration as Code**: Farm rules versioned alongside code

### 2. Code Style
   - Linting tools: black
   - Type hints required: Yes
   - Docstring format: Google Style

---

## 4. Design Decisions & Constraints

### 1. Performance
- **Current Load**: ~100 messages/second
- **Target Load**: Up to 500 messages/second
- **Processing Model**: Synchronous (no batching required at current scale)
- **Scalability**: Horizontal scaling via multiple consumer instances

### 2. Error Handling
- **Philosophy**: Fail fast, log and continue
- **No Retry Logic**: Failed messages are logged and skipped
- **No Dead Letter Queue**: Simplicity over guaranteed delivery
- **Monitoring**: Components monitored via logs only (no Prometheus self-metrics)

### 3. Consumer Group Strategy
- **Dynamic Naming**: Consumer group name includes date+hour suffix (e.g., `ovn-metrics-group-2025010909`)
- **Purpose**: Allows fresh consumption windows without offset conflicts
- **Partition Assignment**: Kafka handles automatic partition distribution
- **Rebalancing**: Minimal manual intervention, rely on Kafka's built-in coordination

### 4. Logging

Both components log to files with automatic rotation:

- **Format**: JSON structured logs
- **Rotation**: Files rotate after reaching 50MB
- **Retention**: Keep last 5 rotated log files
- **Level**: Configurable via `LOG_LEVEL` environment variable

**Log Fields**:
```json
{
  "timestamp": "2025-01-09T09:50:01Z",
  "level": "INFO",
  "component": "raw_to_json",
  "message": "Processed message",
  "context": {
    "topic": "ovn-metrics-raw",
    "partition": 0,
    "offset": 12345
  }
}
```
### 5. Scaling

The raw_to_json component is designed for horizontal scaling:

- **Default**: 2 consumer instances
- **Scaling Method**: Add more container instances
- **Partition Distribution**: Kafka automatically distributes partitions across consumers in the same group
- **Stateless**: Each instance operates independently with no shared state

**Current Performance**:
- Message volume: ~100 messages/second
- Expected growth: Up to 500 messages/second
- Processing: Synchronous, no batching

### 6. Technology Stack

- **Language**: Python 3.10
- **Kafka Client**: confluent_kafka
- **Prometheus Client**: prometheus_client
- **Config**: PyYAML for farm rules parsing
- **Logging**: Python standard logging with JSON formatter
- **Container Base**: `python:3.10` (official Docker Hub image)
- **Orchestration**: Docker Compose / Docker

---

## 5. Architecture

[Section to be completed]

**Questions for Architecture Section:**

1. **Architecture Diagram**:
   - This section contains Mermaid.js diagram

2. **Component Details**:
   - This section contains the core functions and their usage, pseudocode if needed. 

---

## 6. Deployment


Build and start all services in detached mode:

```bash
docker-compose up -d --build
```

To start only one service (e.g., only `raw_to_json`):

```bash
# Build and start raw_to_json only
docker-compose up -d --build raw_to_json

# Build and start json_to_prometheus only
docker-compose up -d --build json_to_prometheus
```

To scale the `raw_to_json` service horizontally (increase consumer instances):

```bash
# Scale raw_to_json to 5 instances
docker-compose up -d --scale raw_to_json=5
```

To stop only one service without affecting others:

```bash
# Stop raw_to_json service only
docker-compose stop raw_to_json

# Stop json_to_prometheus service only
docker-compose stop json_to_prometheus
```

Stop all services:

```bash
# Stop services (containers remain)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and remove volumes
docker-compose down -v
```


---
## 7. Config Guide

### Kafka Config
KAFKA_BOOTSTRAP_SERVER=172.25.240.41:9092,172.25.240.42:9092,172.25.240.43:9092
KAFKA_INPUT_TOPIC=ovn-metrics-raw
KAFKA_OUTPUT_TOPIC=ovn-metrics-json
KAFKA_CONSUMER_GROUP=ovn-metrics-group

### Prometheus Client Config
PROMETHEUS_PORT=8001

### Logging Config
LOG_LEVEL=INFO
```

### Farm Rules Configuration

Farm assignment is controlled by `/config/farm_rules.yaml`, which maps hostname patterns to farm identifiers.

**File Location**: Must be mounted at `/config/farm_rules.yaml` in containers.

**Example Configuration**:
```yaml
farm_rules:
  - pattern: "hni-cloud-ops04"
    farm: "hni-ops4"
  
  - pattern: "hcm-cloud-ops03"
    farm: "hcm-ops3"
  
  - pattern: "hni-cloud-hci"
    farm: "hni-hci"
  
  - pattern: "default"
    farm: "other"
```

**Matching Logic**:
- Patterns are checked sequentially from top to bottom
- First matching pattern wins
- If hostname contains the pattern string, it matches
- If no patterns match, falls back to `"other"` farm
- The pattern `"default"` acts as a catch-all

**Adding New Farms**:
Simply add new entries to the YAML file and restart containers. No code changes required.