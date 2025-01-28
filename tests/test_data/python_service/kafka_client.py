from kafka import KafkaConsumer, KafkaProducer

class OrderProcessor:
    def __init__(self):
        self.producer = KafkaProducer()
        self.consumer = KafkaConsumer('processed-orders')

    def process_order(self, order_id: str):
        self.producer.send('orders', str(order_id).encode())

    def consume_processed_orders(self):
        for message in self.consumer:
            print(f"Received: {message.value}")