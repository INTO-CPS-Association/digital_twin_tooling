from typing import Optional, Callable, Any, Iterable, Mapping

import pika
import argparse
import json
import threading
import yaml
import logging
import datetime
from datetime import datetime


class SignalProcessingThread(threading.Thread):

    def __init__(self, conf, sig, source_exchange, source_routing_key, target_exchange, target_routing_key,
                 target_json_pack, target_json_path, source_datatype, target_datatype) -> None:
        self.conf = conf
        self.sig = sig
        self.source_exchange = source_exchange
        self.source_routing_key = source_routing_key
        self.target_exchange = target_exchange
        self.target_routing_key = target_routing_key
        self.target_json_pack = target_json_pack
        self.target_json_path = target_json_path
        self.target_json_path = target_json_path
        self.source_datatype = source_datatype
        self.target_datatype = target_datatype
        self.in_channel = None
        super().__init__(daemon=True)

    def stop(self):
        if self.in_channel:
            try:
                self.in_channel.stop_consuming()
            except pika.exceptions.StreamLostError:
                pass

    def run(self) -> None:

        in_server_user = self.conf['servers']['source']['user']
        in_server_password = self.conf['servers']['source']['password']
        in_server_port = self.conf['servers']['source']['port']
        in_server_host = self.conf['servers']['source']['host']

        out_server_user = self.conf['servers']['target']['user']
        out_server_password = self.conf['servers']['target']['password']
        out_server_port = self.conf['servers']['target']['port']
        out_server_host = self.conf['servers']['target']['host']

        in_credentials = pika.PlainCredentials(in_server_user, in_server_password)
        in_parameters = pika.ConnectionParameters(in_server_host, in_server_port, '/', in_credentials)
        in_connection = pika.BlockingConnection(in_parameters)
        self.in_channel = in_connection.channel()
        logging.info("In channel opened for {0}:{1}".format(in_server_host, in_server_port))

        out_credentials = pika.PlainCredentials(out_server_user, out_server_password)
        out_parameters = pika.ConnectionParameters(out_server_host, out_server_port, '/', out_credentials)
        out_connection = pika.BlockingConnection(out_parameters)
        out_channel = out_connection.channel()
        logging.info("In channel opened for {0}:{1}".format(out_server_host, out_server_port))

        # declare out exchanges
        target_exchanges = {self.conf['signals'][s]['target']['exchange'] for s in self.conf['signals'].keys()}
        for exchange in target_exchanges:
            out_channel.exchange_declare(exchange=exchange, exchange_type='direct')

        def callback(ch, method, properties, body):

            # check if we know how to decode time otherwise insert time of arrival here
            # if not isinstance(body, str):
            #     logging.warning("Cannot decode message of type: " + type(body))
            #     return

            if self.source_datatype == "double":
                data = float(body)
            elif self.source_datatype == "int":
                data = int(body)
            elif self.source_datatype == "boolean":
                data = bool(body)
            elif self.source_datatype == "string":
                data = bytes.decode(body, 'utf-8')

            if self.target_datatype == "double":
                data = float(data)
            elif self.target_datatype == "int":
                data = int(data)
            elif self.target_datatype == "boolean":
                data = bool(data)
            elif self.target_datatype == "string":
                data = str(data)

            time_stamp = datetime.now().astimezone().isoformat()

            if self.target_json_pack:
                # check to try and see what happens if data is always there
                # dd={'level':0.0,'valve':0.0}
                # d={target_json_path: data, 'time': time_stamp}
                # dd.update(d)
                # fw_data = json.dumps(dd).encode('utf-8')

                # original
                fw_data = json.dumps({self.target_json_path: data, 'time': time_stamp}).encode('utf-8')



            else:
                # fixme we need to make sure time is present in this data
                fw_data = data

            logging.debug(
                "Forwarding '%r' as '%r' to %s(%s)" % (body, fw_data, self.target_exchange, self.target_routing_key))
            out_channel.basic_publish(self.target_exchange, self.target_routing_key, fw_data)

        if len(self.source_exchange) > 0:
            logging.debug("Declaring in-exchange {0} for signal {1}".format(self.source_exchange, self.sig))
            self.in_channel.exchange_declare(exchange=self.source_exchange, exchange_type='direct')

        logging.debug("Declaring in-queue for signal {0}".format(self.sig))
        result = self.in_channel.queue_declare(queue='', durable=False,
                                               auto_delete=True)  # we just want an auto name queue=in_server_exchange_name,

        logging.debug(
            "Binding in-queue for signal {0} to exchange {1} with routing key {2}".format(self.sig,
                                                                                          self.source_exchange,
                                                                                          self.source_routing_key))
        self.in_channel.queue_bind(exchange=self.source_exchange, routing_key=self.source_routing_key,
                                   queue=result.method.queue)  # , routing_key=queue_name)

        logging.debug(
            "Starting consumer thread for signal {0}".format(self.sig))
        self.in_channel.basic_consume(queue=result.method.queue, auto_ack=True, exclusive=True,
                                      on_message_callback=callback)
        self.in_channel.start_consuming()


def start_processing(conf):
    workers = []
    for signal in conf['signals'].keys():
        source_exchange = conf['signals'][signal]['source']['exchange']
        source_routing_key = conf['signals'][signal]['source']['routing_key']
        source_datatype = conf['signals'][signal]['source']['datatype']

        target_exchange = conf['signals'][signal]['target']['exchange']
        target_routing_key = conf['signals'][signal]['target']['routing_key'] if 'routing_key' in \
                                                                                 conf['signals'][signal][
                                                                                     'target'] else ''
        target_datatype = conf['signals'][signal]['target']['datatype']
        target_json_pack = 'JSON' in conf['signals'][signal]['target']['pack'] if 'pack' in conf['signals'][signal][
            'target'] else False
        target_json_path = conf['signals'][signal]['target']['path'] if 'path' in conf['signals'][signal][
            'target'] else None

        workers.append(SignalProcessingThread(conf,
                                              signal, source_exchange, source_routing_key,
                                              target_exchange, target_routing_key,
                                              target_json_pack, target_json_path,
                                              source_datatype, target_datatype))

    for t in workers:
        t.start()

    # for t in workers:
    #     t.join()
    #
    return workers


def main():
    options = argparse.ArgumentParser()
    options.add_argument("-c", '--config', dest="conf", type=str, required=True, help='Path to a yml config')
    options.add_argument("-v", "--verbose", required=False, help='Verbose', dest='verbose', action="store_true")
    options.add_argument("-l", "--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                         help="Set the logging level")

    args = options.parse_args()

    if args.logLevel:
        logging.basicConfig(level=getattr(logging, args.logLevel))

    with open(args.conf, 'r') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
        workers = start_processing(conf)

        for t in workers:
            t.join()


if __name__ == '__main__':
    main()
