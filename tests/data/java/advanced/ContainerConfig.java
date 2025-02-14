package com.example.kafka;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.KafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.listener.ConcurrentMessageListenerContainer;

@Configuration
public class ContainerConfig {
    
    @Bean(name = "customContainerFactory")
    KafkaListenerContainerFactory<ConcurrentMessageListenerContainer<String, String>> factory(
            ConsumerFactory<String, String> consumerFactory) {
        factory.setConsumerFactory(consumerFactory);
        return factory;
    }

    @KafkaListener(topics = "${kafka.topics.custom}", containerFactory = "customContainerFactory")
    public void listen(String message) {
        // Process message
    }
}
