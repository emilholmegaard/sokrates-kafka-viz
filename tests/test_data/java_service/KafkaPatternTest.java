package com.example;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.annotation.SendTo;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.cloud.stream.annotation.StreamListener;
import org.springframework.cloud.stream.annotation.Input;
import org.springframework.cloud.stream.annotation.Output;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.ProducerFactory;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class KafkaPatternTest {
    private final KafkaTemplate<String, String> kafkaTemplate;
    
    @Value("${kafka.topic.name}")
    private String topicName;
    
    @Value("${spring.kafka.template.default-topic}")
    private String defaultTopic;

    // Producer patterns
    @KafkaProducer(topics = "producer-topic-1")
    public void producerAnnotation() {}

    @SendTo("response-topic")
    public String sendToAnnotation(String message) {
        return "processed";
    }

    @Output("output-topic")
    public void outputAnnotation() {}

    public void producerMethods() {
        // Template methods
        kafkaTemplate.send("template-topic", "message");
        customTemplate.produce("custom-topic", "message");
        
        // Direct producer
        producer.send("direct-topic", "message");
        producer.send(new ProducerRecord<>("record-topic", "message"));
        messageProducer.publish("publish-topic", "message");

        // Producer records
        ProducerRecord<String, String> record = new ProducerRecord<>("explicit-topic", "message");
        MessageRecord<String> msgRecord = new MessageRecord<>("message-topic", "message");
        KafkaMessage msg = new KafkaMessage("kafka-topic", "message");
    }

    // Consumer patterns
    @KafkaListener(topics = "listener-topic-1")
    public void listen(ConsumerRecord<String, String> record) {}

    @KafkaListener(topicPattern = "listener-topic.*")
    public void listenPattern(String message) {}

    @StreamListener("stream-topic")
    public void streamListen(String message) {}

    @Input("input-topic")
    public void inputAnnotation() {}

    public void consumerMethods() {
        // Subscribe methods
        consumer.subscribe(Collections.singletonList("singleton-topic"));
        consumer.subscribe(Arrays.asList("array-topic-1", "array-topic-2"));
        consumer.subscribe(Set.of("set-topic"));
        consumer.subscribe(List.of("list-topic"));
        
        // Configuration
        ConsumerConfig config = new ConsumerConfig();
        config.setTopic("config-topic");

        // Container factory
        @Bean(name = "customContainerFactory")
        KafkaListenerContainerFactory<ConcurrentMessageListenerContainer<String, String>> factory() {
            ConcurrentKafkaListenerContainerFactory<String, String> factory = 
                new ConcurrentKafkaListenerContainerFactory<>();
            factory.setConsumerFactory(consumerFactory());
            return factory;
        }
    }
}
