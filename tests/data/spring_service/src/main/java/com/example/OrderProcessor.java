package com.example;

import org.springframework.cloud.stream.annotation.StreamListener;
import org.springframework.cloud.stream.annotation.EnableBinding;
import org.springframework.cloud.stream.messaging.Processor;
import org.springframework.messaging.handler.annotation.SendTo;

@EnableBinding(Processor.class)
public class OrderProcessor {
    @StreamListener("orders")
    @SendTo("processed-orders")
    public ProcessedOrder processOrder(Order order) {
        return new ProcessedOrder(order.getId());
    }
}