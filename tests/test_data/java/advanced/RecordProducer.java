package com.example.kafka;

import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.beans.factory.annotation.Value;

public class RecordProducer {
    private final Producer<String, String> producer;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final MessageProducer messageProducer;

    @Value("${kafka.topic.name}")
    private String configuredTopic;

    public void sendRecord() {
        producer.send(new ProducerRecord<>("record-topic", "message"));
        messageProducer.publish("publish-topic", "message");
        kafkaTemplate.send(configuredTopic, "configured-message");
    }
}
