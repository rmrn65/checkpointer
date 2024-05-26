import os
from aiokafka import AIOKafkaConsumer
import asyncio

async def consume():
    consumer = AIOKafkaConsumer(
        'my_topic',
        bootstrap_servers=os.environ.get('FW_KAFKA_BOOTSTRAP_SERVERS'),
        group_id=os.environ.get('FW_KAFKA_GROUP_ID'),
        security_protocol=os.environ.get('FW_KAFKA_SECURITY_PROTOCOL'),
        retry_backoff_ms=1000,
        session_timeout_ms=int(os.environ.get('FW_KAFKA_SESSION_TIMEOUT_MS')),
        max_poll_records=int(os.environ.get('FW_KAFKA_MAX_POLL_RECORDS')),
        max_poll_interval_ms=int(os.environ.get('FW_KAFKA_MAX_POLL_INTERVAL_MS')),
        enable_auto_commit=False,
    )
    print('Starting consumer')
    while True:
        try:
            await consumer.start()
            print('Consumer started')
            async for msg in consumer:
                print(f"consumed: {msg.topic}, {msg.partition}, {msg.offset}, {msg.key}, {str(msg.value)}, {msg.timestamp}")
                print(f"committing: topic:{msg.topic} partition:{msg.partition} offset:{msg.offset}")
                await consumer.commit()
            break
        except Exception:
            await consumer.stop()
            print('Consumer start exception')
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            print('Stopping consumer')
            await consumer.stop()

