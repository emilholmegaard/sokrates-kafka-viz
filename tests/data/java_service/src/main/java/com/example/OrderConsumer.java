package com.example;

import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public class OrderConsumer {
    private final KafkaConsumer<String, String> consumer;

    public void consume() {
        consumer.subscribe(java.util.Arrays.asList("orders"));
        ConsumerRecord<String, String> record = consumer.poll(1000).iterator().next();
        processOrder(record.value());
    }

    private void processOrder(String orderData) {
        // Process order
    }
}