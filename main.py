from confluent_kafka import Producer
import asyncio
import time

from message_producer import send_kafka_message
from message_consumer import consume as consume_message
from dotenv import load_dotenv
from kafka.errors import KafkaError

import os

# Load environment variables from .env file
load_dotenv('config/.env')

# Get the Kafka bootstrap servers from environment variables
kafka_bootstrap_servers = os.getenv('FW_KAFKA_BOOTSTRAP_SERVERS')
print(kafka_bootstrap_servers)

# Define the message and topic
message = 'Hello, Kafka'
topic = 'my_topic'

# Send the message to the Kafka topic
def produce():
    # Send the message to the Kafka topic
    asyncio.run(send_kafka_message(message, topic))

def consume():
    asyncio.run(consume_message())
# Run the main function
if __name__ == '__main__':
    consume()