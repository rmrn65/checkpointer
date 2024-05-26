import json
import os

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_default_context


async def send_kafka_message(message, topic):
    producer = AIOKafkaProducer(
        bootstrap_servers=os.environ.get('FW_KAFKA_BOOTSTRAP_SERVERS'),
        value_serializer=serializer,
        sasl_mechanism=os.environ.get('FW_KAFKA_SASL_MECHANISM'),
        sasl_plain_username=os.environ.get('FW_KAFKA_SASL_PLAIN_USERNAME'),
        sasl_plain_password=os.environ.get('FW_KAFKA_SASL_PLAIN_PASSWORD'),
        security_protocol=os.environ.get('FW_KAFKA_SECURITY_PROTOCOL'),
        ssl_context=create_default_context(),
        request_timeout_ms=int(os.environ.get('FW_KAFKA_PRODUCER_REQUEST_TIMEOUT_MS'))
    )
    # Get cluster layout and initial topic/partition leadership information
    await producer.start()
    try:
        # Produce message
        await producer.send_and_wait(topic, message)
    finally:
        # Wait for all pending messages to be delivered or expire.
        await producer.stop()


def serializer(value) -> bytes:
    # if object has toJSON method, use it
    if hasattr(value, 'toJSON'):
        return value.toJSON().encode()
    # else, use json.dumps
    return json.dumps(value).encode()
