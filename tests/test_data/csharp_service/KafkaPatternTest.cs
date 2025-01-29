using Confluent.Kafka;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;

namespace TestService.Kafka
{
    [Topic("attribute-topic")]
    public class KafkaPatternTest
    {
        private readonly IProducer<string, string> producer;
        private readonly IConsumer<string, string> consumer;
        private readonly ProducerConfig producerConfig;
        private readonly ConsumerConfig consumerConfig;

        public KafkaPatternTest(IConfiguration config)
        {
            producerConfig = new ProducerConfig
            {
                Topic = "producer-config-topic",
                BootstrapServers = "localhost:9092"
            };

            consumerConfig = new ConsumerConfig
            {
                Topic = "consumer-config-topic",
                GroupId = "test-group",
                BootstrapServers = "localhost:9092"
            };

            producer = new ProducerBuilder<string, string>(producerConfig).Build();
            consumer = new ConsumerBuilder<string, string>(consumerConfig).Build();
        }

        // Producer patterns
        public async Task ProducerPatternsAsync()
        {
            // Direct producer methods
            await producer.ProduceAsync("direct-topic", new Message<string, string> { Value = "message" });
            producer.Produce("sync-topic", new Message<string, string> { Value = "message" });

            // With builder
            var builder = new ProducerBuilder<string, string>(producerConfig)
                .SetTopic("builder-topic")
                .WithTopic("with-topic");

            // Message patterns
            var message = new KafkaMessage("message-topic", "value");
            await messageProducer.SendAsync("send-topic", message);
        }

        // Consumer patterns
        [KafkaListener("listener-topic")]
        public void ListenerMethod(string message)
        {
        }

        public void ConsumerPatterns()
        {
            // Direct consumer methods
            consumer.Subscribe("direct-topic");
            consumer.Subscribe(new[] { "array-topic" });

            // With builder
            var builder = new ConsumerBuilder<string, string>(consumerConfig)
                .SetTopic("builder-topic")
                .WithTopic("with-topic");

            // Async consume
            await consumer.ConsumeAsync("async-topic");
        }
    }

    public class ProducerSettings 
    {
        public string Topic { get; set; } = "settings-topic";
    }

    public class ConsumerSettings
    {
        public string Topic { get; set; } = "settings-topic";
    }
}