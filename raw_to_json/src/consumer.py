"""
Kafka consumer for raw metric messages.

Handles consumption of raw OVN metrics from input Kafka topic.
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime

from common.kafka_client import KafkaConsumerWrapper
from common.logger import MyLogger


class RawMetricConsumer:
    """
    Consumer for raw OVN metric messages from Kafka.
    
    Reads messages from ovn-metrics-raw topic with consumer group coordination.
    """
    
    def __init__(self):
        """Initialize consumer with configuration from environment variables."""
        self.logger = MyLogger(
            'raw_to_json-consumer',
            'logs/raw_to_json/consumer.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
        self.consumer: Optional[KafkaConsumerWrapper] = None
        self._setup_consumer()
    
    def _setup_consumer(self):
        """
        Configure and initialize Kafka consumer.
        
        Uses environment variables:
        - KAFKA_BOOTSTRAP_SERVER
        - KAFKA_INPUT_TOPIC
        - KAFKA_CONSUMER_GROUP
        """
        bootstrap_server = os.getenv('KAFKA_BOOTSTRAP_SERVER', 'localhost:9092')
        input_topic = os.getenv('KAFKA_INPUT_TOPIC', 'ovn-metrics-raw')
        consumer_group = self._generate_consumer_group()
        
        config = {
            'bootstrap.servers': bootstrap_server,
            'group.id': consumer_group,
            'auto.offset.reset': 'latest',
        }
        
        self.logger.log_with_context(
            MyLogger.INFO,
            "Setting up Kafka consumer",
            bootstrap_server=bootstrap_server,
            topic=input_topic,
            consumer_group=consumer_group
        )
        
        self.consumer = KafkaConsumerWrapper(config)
        self.consumer.consumer.subscribe([input_topic])
        self.topic = input_topic
        
        self.logger.log_with_context(
            MyLogger.DEBUG,
            "Kafka consumer initialized successfully"
        )
     
    def _generate_consumer_group(self) -> str:
        """
        Generate consumer group name with date+hour suffix.
        
        Format: <base_group>-DDMMYYYY-HH
        
        Returns:
            Consumer group name string
        """
        base_group = os.getenv('KAFKA_CONSUMER_GROUP', 'ovn-metrics-group')
        timestamp_suffix = datetime.now().strftime('%d%m%Y-%H')
        return f"{base_group}-{timestamp_suffix}"
    
    def consume_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Consume a single message from Kafka.
        
        Args:
            timeout: Polling timeout in seconds
            
        Returns:
            Parsed message dictionary or None
        """
        try:
            msg = self.consumer.consume(timeout=timeout)
            
            if msg is None:
                return None
            
            self.logger.log_with_context(
                MyLogger.DEBUG,
                "Consumed message from Kafka",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                value=msg.value().decode('utf-8') if msg.value() else None
            )
            
            return msg.value().decode('utf-8') if msg.value() else None
            
        except Exception as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Error consuming message from Kafka",
                error=str(e)
            )
            return None
    
    def close(self):
        """Close consumer and commit offsets."""
        if self.consumer:
            self.logger.log_with_context(MyLogger.INFO, "Closing Kafka consumer")
            self.consumer.close()
            self.logger.log_with_context(MyLogger.INFO, "Kafka consumer closed successfully")
