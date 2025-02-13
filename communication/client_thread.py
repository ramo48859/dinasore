import threading
import logging

logger = logging.getLogger("dinasore")


class ClientThread(threading.Thread):
    def __init__(self, connection, client_address, config_m):
        threading.Thread.__init__(
            self, name="{0}:{1}".format(client_address[0], client_address[1])
        )

        self.config_m = config_m
        self.connection = connection
        self.client_address = client_address

    def run(self):
        try:
            logger.info("connection from {0}".format(self.client_address))

            # Receive the data in small chunks and retransmit it
            while True:
                data = self.connection.recv(2048)
                logger.debug("received {0}".format(data))

                if data:
                    response = self.parse_request(data)
                    logger.debug("sending response {0}".format(response))
                    self.connection.sendall(response)

                else:
                    logger.info("no more data from {0}".format(self.client_address))
                    break

        finally:
            # Clean up the connection
            self.connection.close()

    def remove_service_symbols(self, data):
        if "&apos;" in data:
            data = data.replace("&apos;", "")
            logger.error(f"After replacement: {data}")
        elif "&quote;" in data:
            data = data.replace("&quote;", "")
            logger.error(f"After replacement: {data}")
        return data

    def parse_request(self, data):
        config_id_size = int(data[1:3].hex(), 16)

        if config_id_size == 0:
            data_str = data[6:].decode("utf-8")
            data_str = self.remove_service_symbols(data_str)
            response = self.config_m.parse_general(data_str)
        else:
            config_id = data[3 : config_id_size + 3].decode("utf-8")
            data_str = data[config_id_size + 3 + 3 :].decode("utf-8")
            data_str = self.remove_service_symbols(data_str)
            response = self.config_m.parse_configuration(data_str, config_id)

        return response
