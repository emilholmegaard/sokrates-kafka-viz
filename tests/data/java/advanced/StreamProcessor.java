package com.example.kafka;

import org.springframework.cloud.stream.annotation.StreamListener;
import org.springframework.cloud.stream.messaging.Processor;
import org.springframework.messaging.Message;
import org.springframework.context.annotation.Bean;
import java.util.function.Function;

public class StreamProcessor {
    
    @Bean
    public Function<Message<String>, Message<String>> process() {
        return message -> {
            // Process message
            return message;
        };
    }

    interface CustomProcessor {
        @Output("outputChannel")
        MessageChannel output();

        @Input("inputChannel")
        SubscribableChannel input();
    }

    @StreamListener(target = Processor.INPUT)
    @SendTo(Processor.OUTPUT)
    public String transformMessage(String payload) {
        return payload.toUpperCase();
    }
}
