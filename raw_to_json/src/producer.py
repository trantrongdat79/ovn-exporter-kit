"""
Kafka producer for JSON metric messages.

Publishes structured JSON metrics to output Kafka topic.
"""

import os
from typing import List

from common.kafka_client import KafkaProducerWrapper
from common.logger import MyLogger


class JsonMetricProducer:
    """
    Producer for structured JSON metric messages.
    
    Publishes messages to ovn-metrics-json topic.
    """
    
    def __init__(self):
        """Initialize producer with configuration from environment variables."""
        self.logger = MyLogger(
            'raw_to_json-producer',
            'logs/raw_to_json/producer.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
        self.producer: KafkaProducerWrapper = None
        self.output_topic = os.getenv('KAFKA_OUTPUT_TOPIC', 'ovn-metrics-json')
        self._setup_producer()
    
    def _setup_producer(self):
        """
        Configure and initialize Kafka producer.
        
        Uses environment variable:
        - KAFKA_BOOTSTRAP_SERVER
        """
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVER', 'localhost:9092')
        config = {
            'bootstrap.servers': bootstrap_servers,
        }
        self.producer = KafkaProducerWrapper(config)
        self.logger.log_with_context(
            MyLogger.INFO,
            "Kafka producer initialized",
            bootstrap_servers=bootstrap_servers,
            output_topic=self.output_topic
        )
    
    def produce_messages(self, messages: List[str]):
        """
        Produce list of metric messages to Kafka.
        
        Args:
            messages: List of JSON strings to publish
        """        
        for msg in messages:
            self.producer.produce(self.output_topic, msg)
        
        self.producer.poll(0)

        self.logger.log_with_context(
            MyLogger.DEBUG,
            "Produced batch to Kafka",
            message_count=len(messages),
            topic=self.output_topic
        )
    
    def flush(self, timeout: float = 1.0):
        """
        Flush pending messages.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        if self.producer:
            try:
                self.producer.flush(timeout=timeout)
                self.logger.log_with_context(MyLogger.DEBUG, "Periodic flush completed")
            except Exception as e:
                self.logger.log_with_context(
                    MyLogger.ERROR,
                    "Failed to flush Kafka producer",
                    error=str(e)
                )
    
    def close(self):
        """
        Close producer.
        """
        if self.producer:
            try:
                self.producer.flush()
                self.logger.log_with_context(MyLogger.DEBUG, "Kafka Producer cleanup flush completed")
            except Exception as e:
                self.logger.log_with_context(
                    MyLogger.ERROR,
                    "Failed to flush Kafka producer during close",
                    error=str(e)
                )
            self.logger.log_with_context(MyLogger.INFO, "Kafka Producer closed")
