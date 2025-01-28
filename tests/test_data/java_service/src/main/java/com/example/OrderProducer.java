package com.example;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

public class OrderProducer {
    private final KafkaProducer<String, String> producer;

    public void sendOrder(String orderId) {
        ProducerRecord<String, String> record = new ProducerRecord<>("orders", orderId, "order-data");
        producer.send(record);
    }
}