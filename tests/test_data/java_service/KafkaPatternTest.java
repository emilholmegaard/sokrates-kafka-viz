package com.example;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.annotation.SendTo;
import org.springframework.kafka.core.KafkaTemplate;

@Service
public class KafkaPatternTest {
    private final KafkaTemplate<String, String> kafkaTemplate;

    @KafkaListener(topics = "orders")
    @SendTo("processed-orders")
    public void processMessage(String message) {
        return "processed";
    }

    public void sendMessage(String message) {
        kafkaTemplate.send("notifications", message);
    }
}