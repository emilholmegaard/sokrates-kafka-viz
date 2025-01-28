package com.example;

import org.springframework.cloud.stream.annotation.StreamListener;
import org.springframework.cloud.stream.annotation.EnableBinding;
import org.springframework.cloud.stream.messaging.Processor;
import org.springframework.messaging.handler.annotation.SendTo;

@EnableBinding(Processor.class)
public class OrderProcessor {
    @StreamListener(Processor.INPUT)
    @SendTo(Processor.OUTPUT)
    public ProcessedOrder processOrder(Order order) {
        return new ProcessedOrder(order.getId());
    }
}