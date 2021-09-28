import time

from testcontainer_python_rabbitmq import RabbitMQContainer

import unittest
import pika
import threading
from digital_twin_tooling.amqp_data_repeater import start_processing
import logging


class AmpqDataWriterAndReceiverTests(unittest.TestCase):

    # def test_rabbitmq(self):
    #
    #     amqp_server_config = {"server": "localhost",
    #                           "port": 5672,
    #                           "user": "guest",
    #                           "password": "guest",
    #                           "protocol": "amqp"}
    #
    #     out_q = queue.Queue()
    #     in_q = queue.Queue()
    #     sender = AmqpWriter(amqp_server_config, "test_queue", out_q)
    #     receiver = AmqpReceiver(amqp_server_config, "test_queue", in_q)
    #
    #     sender.open()
    #     receiver.open()
    #
    #     out_q.put(12345)
    #     data = in_q.get(timeout=5)
    #     self.assertEqual(12345, data)

    def test_rabbitmq(self):

        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')

        logging.getLogger('urllib3').setLevel(logging.ERROR)
        logging.getLogger('pika').setLevel(logging.ERROR)

        config = RabbitMQContainer(image="rabbitmq:3.9.5-management")
        with config as container:
            print(config.get_url())
            amqp_server_config = {"server": container.get_container_host_ip(),
                                  "port": container.get_amqp_port(),
                                  "user": "guest",
                                  "password": "guest",
                                  "protocol": "amqp"}

            conf = {"servers": {"source": {"host": container.get_container_host_ip(), "password": "guest",
                                           "port": container.get_amqp_port(), "user": "guest"},
                                "target": {"host": container.get_container_host_ip(), "password": "guest",
                                           "port": container.get_amqp_port(), "user": "guest"}},
                    "signals": {"level": {"source": {"exchange": "test",
                                                     "routing_key": "level",
                                                     "datatype": "double"},
                                          "target": {"exchange": "fmi_digital_twin", "pack": "JSON", "path": "level",
                                                     "routing_key": "route-key", "datatype": "double"}},
                                "valve": {"source": {"exchange": "test",
                                                     "routing_key": "valve", "datatype": "boolean"},
                                          "target": {"exchange": "fmi_digital_twin", "pack": "JSON", "path": "valve",
                                                     "routing_key": "route-key", "datatype": "boolean"}}}}

            credentials = pika.PlainCredentials("guest", "guest")
            parameters = pika.ConnectionParameters(container.get_container_host_ip(), container.get_amqp_port(), '/',
                                                   credentials)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            for exchange in ["test", "fmi_digital_twin"]:
                channel.exchange_declare(exchange=exchange, exchange_type='direct')

            # def run_repeater():
            proxy_workers = start_processing(conf)

            # threading.Thread(target=run_repeater,
            #                  daemon=True).start()

            # start consuming the repeated messages

            class MessageCounter:

                def __init__(self) -> None:
                    self.count = 0

                def increment(self):
                    self.count += 1

            counter = MessageCounter()

            def observer():

                def callback(ch, method, properties, body):
                    # print("Received %r" % body)
                    counter.increment()

                connection2 = pika.BlockingConnection(parameters)
                channel2 = connection2.channel()

                result2 = channel2.queue_declare(queue='', durable=False,
                                                 auto_delete=True)  # we just want an auto name queue=in_server_exchange_name,
                channel2.queue_bind(exchange="fmi_digital_twin", routing_key="route-key",
                                    queue=result2.method.queue)  # , routing_key=queue_name)

                channel2.basic_consume(queue=result2.method.queue, auto_ack=True, exclusive=True,
                                       on_message_callback=callback)
                channel2.start_consuming()

            threading.Thread(target=observer,
                             daemon=True).start()

            print("sending test data")
            time.sleep(2)
            for i in range(0, 1000):
                channel.basic_publish(exchange='test', routing_key="level", body=str(i).encode('utf-8'))
                channel.basic_publish(exchange='test', routing_key="valve", body=str(i).encode('utf-8'))

            time.sleep(5)
            for worker in proxy_workers:
                worker.stop()
            print(counter.count)
            self.assertEqual(counter.count, 1000 * 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')
    unittest.main()
