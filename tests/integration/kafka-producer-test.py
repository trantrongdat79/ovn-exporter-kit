from confluent_kafka import Producer
from datetime import datetime
import time

if __name__ == "__main__":
    p = Producer({'bootstrap.servers': '172.25.240.41:9092,172.25.240.42:9092,172.25.240.43:9092', 'linger.ms': 0})
    for i in range(2):
        p.produce('dattt-metrics-test', key='key1', value=f'Datetime: {datetime.now().isoformat()}')
        p.produce('dattt-metrics-test', key='key1', value=f'Datetime: {datetime.now().isoformat()}')
        time.sleep(0.1)
        p.produce('dattt-metrics-test', key='key1', value=f'Datetime: {datetime.now().isoformat()}')
        p.produce('dattt-metrics-test', key='key1', value=f'Datetime: {datetime.now().isoformat()}')
    print(f"At {datetime.now().isoformat()} - Number of events produced: ", len(p))
    time.sleep(0.0001)
    print(f"At {datetime.now().isoformat()} - Number of events polled: ", p.poll(0))
    print(f"At {datetime.now().isoformat()} - Number of events left: ", len(p))

    p.flush()

    # p.produce_batch('dattt-metrics-test', [
    #     {'value': f'Batch message 1 at {datetime.now().isoformat()}'},
    #     {'value': f'Batch message 2 at {datetime.now().isoformat()}'}
    # ])
    p.flush()
    import confluent_kafka
    print(confluent_kafka.__version__)
    import confluent_kafka
    print(confluent_kafka.libversion())

