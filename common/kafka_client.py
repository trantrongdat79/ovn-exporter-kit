"""
Kafka client wrapper utilities.

Provides high-level abstractions for Kafka producers and consumers
with consistent error handling and configuration management.
"""

from typing import Optional, Dict, Any
from confluent_kafka import Consumer, Producer


class KafkaConsumerWrapper:
    """
    Wrapper for Kafka consumer with simplified configuration and error handling.
    
    Handles connection management, offset commits, and graceful shutdown.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Kafka consumer.
        
        Args:
            config: Kafka consumer configuration dictionary
        """
        self.consumer = Consumer(config)
        self.config = config
    
    def consume(self, timeout: float = 1.0):
        """
        Consume a single message from Kafka.
        
        Args:
            timeout: Polling timeout in seconds
            
        Returns:
            Message object or None if timeout
        """
        msg = self.consumer.poll(timeout=timeout)
        
        if msg is None:
            return None
            
        if msg.error():
            from confluent_kafka import KafkaError
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition, not an error
                return None
            else:
                raise Exception(f"Kafka consumer error: {msg.error()}")
        
        return msg
    
    def close(self):
        """Gracefully close consumer and commit offsets."""
        if self.consumer:
            self.consumer.close()


class KafkaProducerWrapper:
    """
    Wrapper for Kafka producer with simplified configuration and error handling.
    
    Handles message serialization, delivery reports, and buffering.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Kafka producer.
        
        Args:
            config: Kafka producer configuration dictionary
        """
        self.producer = Producer(config)
        self.config = config
    
    def produce(self, topic: str, value: str, key: Optional[str] = None):
        """
        Produce a message to Kafka topic.
        
        Args:
            topic: Target Kafka topic
            value: Message value (JSON string)
            key: Optional message key for partitioning
        """
        self.producer.produce(topic=topic, value=value, key=key)
    
    def poll(self, timeout: float = 0.0):
        """
        Poll producer for delivery reports.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        self.producer.poll(timeout)

    def produce_batch(self, topic: str, messages: list):
        """
        Produce a batch of messages to Kafka topic.
        
        Args:
            topic: Target Kafka topic
            messages: List of message dictionaries with 'value' key
        """
        self.producer.produce_batch(topic, messages)
    
    def flush(self, timeout: float = 1.0):
        """
        Flush pending messages and wait for delivery.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        self.producer.flush(timeout=timeout)