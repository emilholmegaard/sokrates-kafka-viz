package com.example.kafka;

import org.apache.kafka.clients.consumer.Consumer;
import org.springframework.kafka.annotation.KafkaListener;
import java.util.Arrays;
import java.util.Set;

public class CollectionConsumer {
    private final Consumer<String, String> consumer;

    public void subscribeToTopics() {
        consumer.subscribe(Arrays.asList("topic1", "topic2"));
        consumer.subscribe(Set.of("topic3", "topic4"));
    }

    @KafkaListener(topics = {"topic5", "topic6"})
    public void listen(String message) {
        // Process message
    }
}
