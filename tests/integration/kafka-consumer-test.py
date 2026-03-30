# Kafka Consumer Test Script
from confluent_kafka import Consumer

if __name__ == "__main__":
    config = {
        'bootstrap.servers': '172.25.240.41:9092,172.25.240.42:9092,172.25.240.43:9092',
        'group.id': 'kafka-consumer-test-group',
        'auto.offset.reset': 'latest',
    }

    print("Starting Kafka consumer test...")
    consumer = Consumer(config)
    consumer.subscribe(["dattt-metrics-test"])

    try:
        while True:
            messages = consumer.consume(timeout=1.0)
            if messages is None:
                continue
            else:
                for message in messages:
                    print(f"Received message: {message.value().decode('utf-8')}")

    except KeyboardInterrupt:
        consumer.close()
        print("Shutting down consumer...")