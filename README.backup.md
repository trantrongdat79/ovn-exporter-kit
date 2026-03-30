# OVN Exporter Kit

A containerized Kafka-based data pipeline for collecting, processing, and exporting OVN (Open Virtual Network) metrics to Prometheus. This kit transforms raw metric logs into structured JSON format and exposes them via Prometheus client for monitoring and visualization.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Farm Rules Configuration](#farm-rules-configuration)
- [Components](#components)
  - [1. ovn-metric-raw-to-json](#1-ovn-metric-raw-to-json)
  - [2. ovn-metric-json-to-prometheus](#2-ovn-metric-json-to-prometheus)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Logging](#logging)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Problem Statement
OVN infrastructure generates coverage metrics that need to be monitored and visualized. These metrics are collected via cron jobs and exported to Kafka in raw format by tools like Filebeat or Fluentd. A processing pipeline is required to transform these raw metrics into structured formats suitable for time-series databases like Prometheus.

### Solution
The OVN Exporter Kit provides a two-stage pipeline:

1. **Stage 1 (Raw-to-JSON)**: Consumes raw metric messages from Kafka, parses and normalizes them, extracts metadata (host, farm, component), and publishes structured JSON metrics back to Kafka.

2. **Stage 2 (JSON-to-Prometheus)**: Consumes structured JSON metrics from Kafka and exposes them via a Prometheus-compatible HTTP endpoint for scraping.

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
                                          [ovn-metric-raw-to-json]
                                                      ↓
                                             Kafka (ovn-metrics-json)
                                                      ↓
                                        [ovn-metric-json-to-prometheus]
                                                      ↓
                                          Prometheus HTTP Endpoint (Port 8001)
                                                      ↓
                                              Grafana Dashboards
```

---

## Architecture

[Section to be completed]

**Questions for Architecture Section:**

1. **Architecture Diagram**: Would you like me to create:
   - ASCII art diagram?
   - Mermaid.js diagram (renders on GitHub)?
   - Both?

2. **Component Details**: Should the diagram show:
   - Kafka partition distribution?
   - Number of consumer instances (2x raw-to-json)?
   - Container orchestration platform (Docker Compose, Kubernetes, plain Docker)?

3. **Infrastructure Details**: Do you want to include:
   - Kafka cluster topology (3 brokers from your .env)?
   - Network architecture?
   - Where does Prometheus scrape from (all container instances or load balancer)?

---

## Development Guide

[Section to be completed]

**Questions for Development Guide Section:**

1. **Project Structure**: Should I define the directory structure? Something like:
   ```
   ovn-exporter-kit/
   ├── raw-to-json/
   │   ├── src/
   │   ├── Dockerfile
   │   └── requirements.txt
   ├── json-to-prometheus/
   │   ├── src/
   │   ├── Dockerfile
   │   └── requirements.txt
   ├── config/
   │   └── farm_rules.yaml
   ├── common/           # Shared utilities?
   ├── .env
   ├── docker-compose.yml
   └── README.md
   ```

2. **Development Workflow**: What should developers know about:
   - How to set up local development environment?
   - How to run components locally (outside Docker)?
   - How to run tests (you mentioned simple tests for later)?

3. **Code Style**: Conventions:
   - Linting tools: black
   - Type hints required: Yes
   - Docstring format: Google Style

---

## Deployment

[Section to be completed]

**Questions for Deployment Section:**

1. **Orchestration Platform**: Which deployment method should I document:
   - Docker Compose (simplest)?
   - Kubernetes (production-grade)?
   - Plain Docker commands?
   - All of the above?

2. **Scaling Instructions**: For horizontal scaling, should I include:
   - Docker Compose scale command: `docker-compose up -d --scale raw-to-json=5`?
   - Kubernetes replica configuration?
   - Manual container spawning?

3. **Configuration Management**: How are configs deployed:
   - Volume mounts for `farm_rules.yaml`?
   - ConfigMaps (if K8s)?
   - Baked into image?

4. **Image Building**: Should I include:
   - How to build Docker images?
   - Image naming convention?
   - Push to registry instructions?

**Suggested Outline (pending your answers):**
```markdown
## Deployment

### Using Docker Compose (Recommended)
[docker-compose up commands]

### Manual Docker Deployment
[docker build and docker run commands]

### Scaling
[How to add more raw-to-json instances]

### Health Checks
[How to verify components are running]
```

---

## Components
### 1. ovn-metric-raw-to-json

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
For example: This message contains 4 metrics hence 4 messages:
```md
[COVERAGE] [2025-01-09 09:50:01]util_xalloc              5127.0/sec  4746.300/sec     4774.4800/sec   total: 3124016321
```
### 2. ovn-metric-json-to-prometheus

**Purpose**: Kafka consumer that exposes JSON metrics via Prometheus HTTP endpoint.

**Input**: Kafka topic `ovn-metrics-json` - Structured JSON metrics from raw-to-json component  
**Output**: Prometheus client HTTP endpoint on port `8001` with full metrics and lables, refresh every 1 minutes

---

# Design Decisions & Constraints

### Performance
- **Current Load**: ~100 messages/second
- **Target Load**: Up to 500 messages/second
- **Processing Model**: Synchronous (no batching required at current scale)
- **Scalability**: Horizontal scaling via multiple consumer instances

### Error Handling
- **Philosophy**: Fail fast, log and continue
- **No Retry Logic**: Failed messages are logged and skipped
- **No Dead Letter Queue**: Simplicity over guaranteed delivery
- **Monitoring**: Component health monitored via logs only (no Prometheus self-metrics)

### Consumer Group Strategy
- **Dynamic Naming**: Consumer group name includes date+hour suffix (e.g., `ovn-metrics-group-2025010909`)
- **Purpose**: Allows fresh consumption windows without offset conflicts
- **Partition Assignment**: Kafka handles automatic partition distribution
- **Rebalancing**: Minimal manual intervention, rely on Kafka's built-in coordination

### Testing Strategy
- **Current Phase**: Testing framework to be implemented in future iterations
- **Planned**: Simple unit tests for message parsing and transformation logic
- **Planned**: Basic integration tests for end-to-end pipeline validation
- **Not Required**: Kafka mocking (use real Kafka for integration tests)

---

## Technology Stack

- **Language**: Python 3.10
- **Kafka Client**: kafka-python (or confluent-kafka-python)
- **Prometheus Client**: prometheus_client
- **Config**: PyYAML for farm rules parsing
- **Logging**: Python standard logging with JSON formatter
- **Container Base**: `python:3.10` (official Docker Hub image)
- **Orchestration**: Docker Compose / Docker

---
# Kafka Config
KAFKA_BOOTSTRAP_SERVER=172.25.240.41:9092,172.25.240.42:9092,172.25.240.43:9092
KAFKA_INPUT_TOPIC=ovn-metrics-raw
KAFKA_OUTPUT_TOPIC=ovn-metrics-json
KAFKA_CONSUMER_GROUP=ovn-metrics-group

# Prometheus Client Config
PROMETHEUS_PORT=8001

# Logging Config
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

---

## Logging

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
  "component": "raw-to-json",
  "message": "Processed message",
  "context": {
    "topic": "ovn-metrics-raw",
    "partition": 0,
    "offset": 12345
  }
}
```

---

## Scaling

### Horizontal Scaling (ovn-metric-raw-to-json)

The raw-to-json component is designed for horizontal scaling:

- **Default**: 2 consumer instances
- **Scaling Method**: Add more container instances
- **Partition Distribution**: Kafka automatically distributes partitions across consumers in the same group
- **Stateless**: Each instance operates independently with no shared state

**Current Performance**:
- Message volume: ~100 messages/second
- Expected growth: Up to 500 messages/second
- Processing: Synchronous, no batching

---

## Troubleshooting

[Section to be reserved for common issues and solutions]

---
**Field Descriptions**:
- `command`: Metric type (e.g., "coverage")
- `time`: Timestamp from the original log
- `metric`: Metric name extracted from log message
- `host`: Hostname from input message
- `farm`: Farm identifier determined by hostname pattern matching
- `component`: OVN component extracted from log file path (e.g., "ovn-nb-db")
- `info_5s`, `info_1m`, `info_1h`, `total`: Metric values for different time intervals

{
    "message":"[COVERAGE] [2025-01-09 09:50:01] util_xalloc              5127.0/sec  4746.300/sec     4774.4800/sec   total: 3124016321"
    "log_path":"/home/admin/log/openvswitch/ovn-nb-db-coverage.log"
    "hostname":"host1"
}

### The message Output should be following this format:
Message 1: {"command":"coverage","time":"2025-01-09 09:50:01", "metric":"util_xalloc","host":"host1","farm":"farm1","component":"ovn-nb-db","info_5s":5127.0}
Message 2: {"command":"coverage","time":"2025-01-09 09:50:01", "metric":"util_xalloc","host":"host1","farm":"farm1","component":"ovn-nb-db","info_1m":4746.300}
Message 3: {"command":"coverage","time":"2025-01-09 09:50:01", "metric":"util_xalloc","host":"host1","farm":"farm1","component":"ovn-nb-db","info_1h":4774.4800}
Message 4: {"command":"coverage","time":"2025-01-09 09:50:01", "metric":"util_xalloc","host":"host1","farm":"farm1","component":"ovn-nb-db","total":3124016321}

## 2. ovn-metric-json-to-prometheus
Input: Kafka Consumer from topic "B", expect ovn-metric in JSON format
Output: Export ovn-metric using prometheus client
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_5s",metric="util_xalloc"} 5127.0
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_1m",metric="util_xalloc"} 4746.300
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="info_1h",metric="util_xalloc"} 4774.4800
coverage{component="ovn-nb-db",host="host1",farm="farm1",interval="total",metric="util_xalloc"} 3124016321

# Additional Information
## 1. Programming Language
Python 3.10

## 2. Deployment Model
- Both components will be deployed under a Containerized environment.
- Each components will be a separate container, so that the user could scale easily (for example increase the number of ovn-metric-raw-to-json workers/containers)
- This project is managed in One Repo

## 3. Configuration
- The configurations will be passed using Env vars for secrets, config files for structure
- Farm Assignment logic is simple: The "host" will contains a string that tells its farm. For example:
    farm_rules:
    - pattern contain: "hni-cloud-ops04"
        farm: "hni-ops4"
    - pattern: "hcm-cloud-ops03"
        farm: "hcm-ops3"
    - pattern: "hni-cloud-hci"
        farm: "hni-hci"
    - other: 
        farm: "other"
Currently this is all of the cases, but the program should be designed so that this list is easily adjusted.

## 4. Scale & Performance
- The message volume is currently around 100 messages per second, expect scaling to 500 messages per second after a few months. 
- Messages batch processing is not nessesary at the moment. Basic kafka.KafkaConsumer, synchronous processing is expected at the moment for simplicity.
- Number of ovn-metric-raw-to-json is two by default. Scaling action should be simple by adding more running containers (stateless design). Group coordination, rebalancing handling should be minimal (or remove) for simplicity if kafka can handle by itself.
- Single Consumer Group for Kafka auto partitions distributions

## 5. Error Handling and Logging
- Message Processing does not need retry, log error and move on
- No need Dead Letter Queue
- Only Logging in JSON (log to file, rotate after file reach 50MB, rotate 5).
- Do not need prometheus metrics for components's monitoring
- Error Handling should be kept simple

## 6. Testing:
- Unit Test should be simple, we will get back to this latter
- Intergration Test should be simple, we will get back to this latter
- Mock Kafka is not necessary at the moment

## 7. Environments Variables
- Environments Variables are in .env file, please reference for more detail

## 8. Config File
- config farm mapping is in /config/farm_rules.yaml and mounted as volume to the container
## 9. Not need currently
- No project License
- No github Repo (I'll add myself later)
- Docker images can pull from public Docker Hub: for example "FROM python:3.10"
