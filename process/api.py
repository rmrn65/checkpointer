import json
import os

import httpx
import random
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_default_context
from dotenv import load_dotenv

load_dotenv('config/.env')

PORT = os.environ.get('PORT', 8081)
HOST = os.environ.get('HOST', 'localhost')
ACCOUNT= os.environ.get('ACCOUNT', 'default')
CAMERA = os.environ.get('CAMERA', "false")
MICROPHONE = os.environ.get('MICROPHONE', "false")
BACKGROUND = os.environ.get('BACKGROUND', 0)
CONNECTED_USERS = []
CHECKPOINTER_HOST = os.environ.get('CHECKPOINTER_HOST', 'localhost')


class Host(BaseModel):
    hostname: str
class Message(BaseModel):
    message: str
class Update(BaseModel):
    camera: str
    microphone: str
    background: str

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
    #todo: try this in a loop
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

def produce(message: str):
    # Send the message to the Kafka topic
    asyncio.run(send_kafka_message(message, "checkpoint"))

def process_packet(packet):
    print(f"User {packet.account} sent a message: {packet.message}; "
          f"camera_on: {packet.camera}; microphone_on: {packet.microphone}; "
          f"background: {packet.background}")


def send_a_packet(message, host):
    print(f"Sending packet to {host}")
    response = httpx.post(
        f'http://{host}/receive',
        json={
            "packet_id": random.randint(1, 100),
            "camera": CAMERA,
            "microphone": MICROPHONE,
            "background": BACKGROUND,
            "message": message.message,
            "account": ACCOUNT
        }
    )
    if response.status_code != 200:
        print(f"Failed to send packet to {host}")


app = FastAPI()


class Packet(BaseModel):
    packet_id: int
    camera: str
    microphone: str
    background: int
    message: str
    account: str


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.post("/connect")
async def connect(host: Host):
    response = httpx.get(f"http://{host.hostname}")
    status = response.json()['status']
    if status != 'ok':
        print(f"Failed to connect to {host.hostname}")
        return {"message": "Failed to connect"}
    else:
        CONNECTED_USERS.append(host.hostname)
        await subscribe_to_checkpointer()
    return {"message": "Connected successfully"}


@app.get("/connected")
def connected():
    return {"connected": CONNECTED_USERS}


@app.post("/receive")
def receive_packet(packet: Packet):
    process_packet(packet)
    return {"message": "ACK"}


@app.post("/send")
def send_packet(message: Message):
    for host in CONNECTED_USERS:
        send_a_packet(message, host)
    return {"message": "ACK"}

@app.post("/update")
def update_settings(packet: Update):
    global CAMERA, MICROPHONE, BACKGROUND
    CAMERA = packet.camera
    MICROPHONE = packet.microphone
    BACKGROUND = packet.background
    subscribe_to_checkpointer()
    produce(json.dumps({"camera": CAMERA, "microphone": MICROPHONE, "background": BACKGROUND, "account": ACCOUNT, "connected": CONNECTED_USERS}))
    return {"message": "Settings updated"}

@app.get("/status")
def get_components():
    return {
        "camera": CAMERA,
        "microphone": MICROPHONE,
        "background": BACKGROUND,
        "account": ACCOUNT,
        "connected": CONNECTED_USERS
    }

@app.on_event("startup")
async def startup_event():
    print("Starting up")
    await subscribe_to_checkpointer()
    await get_last_state()
    # Acquire state


async def subscribe_to_checkpointer():
    WAITING_ACK = True
    while WAITING_ACK:
        response = httpx.post(f'http://{CHECKPOINTER_HOST}:8084/update_processes',
                              json={"process": f"{HOST}:{PORT}",
                                    "account": ACCOUNT})
        if response.status_code == 200:
            WAITING_ACK = False
        else:
            print("Failed to get state from checkpointer")
            await asyncio.sleep(5)
async def get_last_state():
    response = httpx.get(f'http://{CHECKPOINTER_HOST}:8084/get_state/{ACCOUNT}')
    if response.status_code == 200:
        data = response.json()
        print(data)
        global CAMERA, MICROPHONE, BACKGROUND, CONNECTED_USERS
        CAMERA = data['camera']
        MICROPHONE = data['microphone']
        BACKGROUND = data['background']
        CONNECTED_USERS = data['connected']
        print(f"Acquired state: camera: {CAMERA}, microphone: {MICROPHONE}, background: {BACKGROUND}")
        return True
    else:
        print("No prior state from checkpointer")
        return False

