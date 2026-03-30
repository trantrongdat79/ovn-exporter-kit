"""
Main entry point for raw_to_json component.

Initializes Kafka consumer, processor, and producer, then runs the main processing loop.
"""

import time
import sys
import os
import signal

from typing import Optional

# Add common package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.logger import MyLogger
from consumer import RawMetricConsumer
from processor import MessageProcessor
from producer import JsonMetricProducer


class RawToJsonService:
    """
    Main service orchestrator for raw_to_json component.
    
    Coordinates consumer, processor, and producer lifecycle.
    """
    
    def __init__(self):
        """Initialize service components."""
        self.logger = None
        self.consumer: Optional[RawMetricConsumer] = None
        self.processor: Optional[MessageProcessor] = None
        self.producer: Optional[JsonMetricProducer] = None
        self.running = False
        self.last_flush_time = time.time()
    
    def setup(self):
        """
        Set up service components from environment variables.
        
        Initializes logger, consumer, processor, and producer.
        """
        # Get configuration from environment
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        if not os.path.exists('logs/raw_to_json'):
            os.makedirs('logs/raw_to_json')
        log_file = os.environ.get('LOG_FILE', '/app/logs/raw_to_json/app.log')
        
        # Initialize logger with JSON formatting and rotation
        self.logger = MyLogger(
            name='ovn-raw-to-json',
            log_file=log_file,
            level=log_level,
            max_bytes=50 * 1024 * 1024,  # 50MB
            backup_count=5
        )
        
        self.logger.log_with_context(MyLogger.INFO, "Starting raw_to_json service")

        # Initialize components
        try:
            self.consumer = RawMetricConsumer()
            self.processor = MessageProcessor()
            self.producer = JsonMetricProducer()
            
            self.logger.log_with_context(MyLogger.DEBUG, "Service components initialized successfully")
        except Exception as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Failed to initialize service components",
                error=str(e)
            )
            raise

    def run(self):
        """
        Main processing loop.
        
        Continuously consumes messages, processes them, and produces results.
        """
        self.running = True
        self.logger.log_with_context(MyLogger.DEBUG, "Starting main processing loop")
        
        while self.running:
            # Consume message from Kafka
            message = self.consumer.consume_message(timeout=1.0)
            
            if message is None:
                # Check if 5 seconds passed since last flush
                if time.time() - self.last_flush_time >= 5.0:
                    self.producer.flush()
                    self.last_flush_time = time.time()
                continue

            # Process message
            processed_messages = self.processor.process(message)
            
            if processed_messages:
                try:
                    # Send messages to Kafka                    
                    self.producer.produce_messages(processed_messages)

                    for msg in processed_messages:
                        self.logger.log_with_context(
                            MyLogger.INFO,
                            "Produced messages to Kafka",
                            message=msg
                        )
                    
                except Exception as e:
                    # Log error, skip message, wait 1 second
                    self.logger.log_with_context(
                        MyLogger.ERROR,
                        "Failed to produce messages to Kafka, skipping batch",
                        error=str(e),
                        message_count=len(processed_messages)
                    )
                    time.sleep(1.0)
            
    def shutdown(self, signum, frame):
        """
        Graceful shutdown handler.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        
        self.logger.log_with_context(MyLogger.INFO, "Received shutdown signal", signal=signal_name, signal_number=signum)
        
        self.running = False
        
        # Cleanup components
        try:
            if self.consumer:
                self.consumer.close()
                self.logger.log_with_context(MyLogger.DEBUG, "Consumer closed successfully")

            if self.processor:
                self.logger.log_with_context(MyLogger.DEBUG, "Processor closed successfully")

            if self.producer:                
                self.producer.close()
                self.logger.log_with_context(MyLogger.DEBUG, "Producer closed successfully")

            self.logger.log_with_context(MyLogger.INFO, "Service shutdown complete")

        except Exception as e:
            self.logger.log_with_context(MyLogger.ERROR, f"Error while shutdown: {str(e)}")

def main():
    """
    Application entry point.
    
    Sets up signal handlers and starts the service.
    """
    service = RawToJsonService()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, service.shutdown)
    signal.signal(signal.SIGTERM, service.shutdown)
    
    service.setup()
    service.run()


if __name__ == "__main__":
    main()
