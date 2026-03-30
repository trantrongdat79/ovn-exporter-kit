"""
Example script demonstrating various logger usage patterns.

This script shows how to use the common.logger module with different
logging levels, contexts, and exception handling.
"""

import sys
import os

# Add common package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import MyLogger


def example_basic_logging():
    """Demonstrate basic logger setup and usage."""
    print("\n=== Example 1: Basic Logging ===")
    
    # Set up logger
    logger = MyLogger(
        name='example-component',
        log_file='logs/example/basic.log',
        level='INFO'
    )
    
    # Different log levels with context
    logger.log_with_context(MyLogger.DEBUG, "This is a debug message")
    logger.log_with_context(MyLogger.INFO, "Service started successfully")
    logger.log_with_context(MyLogger.WARNING, "Resource usage high", cpu_percent=85.5)
    logger.log_with_context(MyLogger.ERROR, "Connection failed", host="localhost", port=9092)


def example_kafka_processing():
    """Demonstrate logging during Kafka message processing."""
    print("\n=== Example 2: Kafka Message Processing ===")
    
    logger = MyLogger(
        name='kafka-processor',
        log_file='logs/example/kafka.log',
        level='INFO'
    )
    
    # Log message consumption
    logger.log_with_context(
        MyLogger.INFO,
        "Consumed message from Kafka",
        topic="ovn-metrics-raw",
        partition=0,
        offset=12345,
        message_size=256
    )
    
    # Log processing metrics
    logger.log_with_context(
        MyLogger.INFO,
        "Processed batch of messages",
        batch_size=100,
        processing_time_ms=1250,
        success_count=98,
        error_count=2
    )


def example_with_default_context():
    """Demonstrate using default context for all log messages."""
    print("\n=== Example 3: Default Context ===")
    
    logger = MyLogger(
        name='service-with-context',
        log_file='logs/example/context.log',
        level='INFO'
    )
    
    # Add default context that will be included in all logs
    logger.add_context(service_version="1.0.0", environment="production")
    
    # All subsequent logs will include the default context
    logger.log_with_context(MyLogger.INFO, "Service started")
    logger.log_with_context(
        MyLogger.INFO,
        "Processing request",
        request_id="req-12345",  # Additional context for this log
        user_id="user-789"
    )


def example_error_handling():
    """Demonstrate exception logging."""
    print("\n=== Example 4: Exception Handling ===")
    
    logger = MyLogger(
        name='error-handler',
        log_file='logs/example/errors.log',
        level='ERROR'
    )
    
    try:
        # Simulate an error
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.log_with_context(
            MyLogger.ERROR,
            "Division by zero error occurred",
            operation="calculate_average",
            input_value=10
        )
        
        # Log with exception info
        logger.logger.error(
            "Unexpected error in calculation",
            exc_info=True,
            extra={
                'component': 'error-handler',
                'context': {'module': 'math_operations', 'function': 'divide'}
            }
        )


def example_performance_monitoring():
    """Demonstrate logging for performance monitoring."""
    print("\n=== Example 5: Performance Monitoring ===")
    
    logger = MyLogger(
        name='performance-monitor',
        log_file='logs/example/performance.log',
        level='INFO'
    )
    
    import time
    
    start_time = time.time()
    
    # Simulate some work
    time.sleep(0.1)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    logger.log_with_context(
        MyLogger.INFO,
        "Operation completed",
        operation="process_metrics",
        duration_ms=round(elapsed_ms, 2),
        items_processed=150,
        throughput_per_sec=round(150 / (elapsed_ms / 1000), 2)
    )


def example_multi_component():
    """Demonstrate multiple components with separate loggers."""
    print("\n=== Example 6: Multiple Components ===")
    
    # Consumer logger
    consumer_logger = MyLogger(
        name='consumer',
        log_file='logs/example/consumer.log',
        level='INFO'
    )
    
    # Processor logger
    processor_logger = MyLogger(
        name='processor',
        log_file='logs/example/processor.log',
        level='INFO'
    )
    
    # Producer logger
    producer_logger = MyLogger(
        name='producer',
        log_file='logs/example/producer.log',
        level='INFO'
    )
    
    # Each component logs independently
    consumer_logger.log_with_context(MyLogger.INFO, "Polling for messages", timeout_ms=1000)
    processor_logger.log_with_context(MyLogger.INFO, "Transforming message", message_id="msg-123")
    producer_logger.log_with_context(MyLogger.INFO, "Publishing to topic", topic="output", partition=2)


if __name__ == "__main__":
    print("Logger Usage Examples")
    print("=" * 50)
    print("\nThese examples demonstrate various logging patterns.")
    print("Check the logs/ directory for JSON-formatted output.\n")
    
    example_basic_logging()
    example_kafka_processing()
    example_with_default_context()
    example_error_handling()
    example_performance_monitoring()
    example_multi_component()
    
    print("\n" + "=" * 50)
    print("Examples completed! Check the logs/example/ directory.")
    print("Each log file contains JSON-structured logs.")
