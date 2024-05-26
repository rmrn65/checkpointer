import json
import time
import httpx
import redis
import os
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aiokafka import AIOKafkaConsumer
import asyncio
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaException


load_dotenv('config/.env')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
PROCESSES = []
CHECKING = True  # This is the new global variable

class Update(BaseModel):
    process: str
    account: str

class Checkpointer:
    def __init__(self, host=REDIS_HOST, port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db)

    def add_data(self, key, value):
        print(f"Adding data to REDIS: {key} {value}")
        self.r.set(key, str(value).replace("'", "\""))

    def get_data(self, key):
        data = self.r.get(key)
        # print(str(data))
        if data is not None:
            return data.decode("utf-8") # todo: must solve this somehow
        return None


app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/get_state/{account}")
async def get_state(account: str):
    checkpointer = Checkpointer()
    data = checkpointer.get_data(account)
    if data is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return json.loads(data)


@app.post("/update_processes")
def update_processes(update: Update):
    global PROCESSES
    for proc in PROCESSES:
        if proc[1] == update.account:
            print(f"Processes: {PROCESSES}")
            return {"message": "Update complete"}
    PROCESSES.append((update.process, update.account))
    print(f"Processes: {PROCESSES}")
    return {"message": "Update complete"}


def check_hosts():
    global CHECKING
    while CHECKING:  # This will make the function run indefinitely
        for proc in PROCESSES:
            host = proc[0]
            try:
                response = httpx.get(f'http://{host}/')
                status = response.json()['status']
                if status != 'ok':
                    print(f"Host {host} is not responding")
                    if proc in PROCESSES:
                        PROCESSES.remove(proc)
                else:
                    print(f"Host {host} is alive")
            except Exception as e:
                print(f"Error checking host {host}: {e}")
                if proc in PROCESSES:
                    PROCESSES.remove(proc)

        time.sleep(5)

def is_host_the_same(data, response):
    if data is None:
        return False

    return (data['camera'] == response.json()['camera']
            and data['microphone'] == response.json()['microphone']
            and data['background'] == response.json()['background']
            and data['account'] == response.json()['account']
            and data['connected'] == response.json()['connected'])

@app.on_event("startup")
async def startup_event():
    print("Starting check hosts thread")
    check_thread = threading.Thread(target=check_hosts, name="Check Hosts")
    check_thread.start()
    consumer_thread = threading.Thread(target=consume_sync, name="Consumer")
    consumer_thread.start()


def consume_sync():
    time.sleep(5)
    kafka_conf = {
        'bootstrap.servers': 'kafka:29092',  # replace with your Kafka server
        'group.id': 'checkpoint',
        'auto.offset.reset': 'earliest',
    }
    CONSUME = True
    while CONSUME:
        try:
            consumer = Consumer(kafka_conf)
            CONSUME = False
        except KafkaException as e:
            print(f"Error creating Kafka consumer: {e}")
            time.sleep(5)
            continue
    consumer.subscribe(['checkpoint'])  # replace with your Kafka topic
    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue
            if msg.error():
                print(msg.error())
                time.sleep(5)
            else:
                # Print the key/value
                print('Received message from KAFKA: {}'.format(msg.value().decode('utf-8')))
                data = json.loads(msg.value().decode('utf-8'))
                map = json.loads(data)
                checkpointer = Checkpointer()
                checkpointer.add_data(map["account"], data)
                # Save the message into Redis
    except KeyboardInterrupt:
        pass

    finally:
        # Close down consumer to commit final offsets.
        consumer.close()
