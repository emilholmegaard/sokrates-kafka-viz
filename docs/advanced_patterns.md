# Advanced Kafka Pattern Support

This document describes the advanced Kafka patterns supported by the analyzer.

## Java Patterns

### Record-based Producers
The analyzer detects topics in the following producer patterns:
```java
// Using ProducerRecord constructor
producer.send(new ProducerRecord<>("record-topic", "message"));

// Using MessageProducer publish method
messageProducer.publish("publish-topic", "message");

// Using KafkaTemplate with configured topics
kafkaTemplate.send(configuredTopic, "message");
```

### Configuration-based Topics
Support for Spring-style configuration properties:
```java
@Value("${kafka.topic.name}")
private String topicName;
```

### Collection-based Subscriptions
Multiple subscription patterns are supported:
```java
// Using Arrays.asList
consumer.subscribe(Arrays.asList("topic1", "topic2"));

// Using Set.of
consumer.subscribe(Set.of("topic3", "topic4"));

// Using @KafkaListener with multiple topics
@KafkaListener(topics = {"topic5", "topic6"})
```

### Container Factory Configurations
Support for custom container factories:
```java
@Bean(name = "customContainerFactory")
KafkaListenerContainerFactory<...> factory() {
    factory.setConsumerFactory(consumerFactory());
}

@KafkaListener(topics = "${kafka.topics.custom}", containerFactory = "customContainerFactory")
```

## Spring Cloud Stream Patterns

### Function-based Bindings
Detection of functional style processors:
```java
@Bean
public Function<Message<String>, Message<String>> process() {
    return message -> ...;
}
```

### Interface-based Bindings
Support for custom processor interfaces:
```java
interface CustomProcessor {
    @Output("outputChannel")
    MessageChannel output();
    
    @Input("inputChannel")
    SubscribableChannel input();
}
```

## Implementation Notes
- The analyzer uses regular expressions to detect these patterns
- Both literal strings and configuration references are supported
- Topics are tracked with their producer/consumer type
- Spring Cloud Stream bindings are mapped to Kafka topics