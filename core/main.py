import logging
import logging.handlers
import os
import sys
import argparse
import glob
import queue
import atexit
import json

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))


# sys.path.insert(0, "F:\Dokumente\Projekte\WechselrichterAuslesen\Dinasore\fronos\dinasore")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "resources"))
# sys.path.insert(0, os.path.join(os.getcwd(),"resources","energy_management_system"))

from communication import tcp_server
from core import manager


logger = logging.getLogger("dinasore")  # __name__ is a common choice


def setup_logging(level):
    # Create a queue for logging
    log_queue = queue.Queue(-1)

    # Create QueueHandler
    queue_handler = logging.handlers.QueueHandler(log_queue)

    # Define the JSON formatter
    class MyJSONFormatter(logging.Formatter):
        def format(self, record):
            record.message = record.getMessage()
            record.asctime = self.formatTime(record, self.datefmt)
            log_record = {
                "level": record.levelname,
                "message": record.message,
                "timestamp": record.asctime,
                "logger": record.name,
                "module": record.module,
                "line": record.lineno,
                "thread_name": record.threadName,
            }
            return json.dumps(log_record)

    pretty_formater = logging.Formatter(
        "[%(levelname)-7s|%(asctime)s.%(msecs)03d|%(threadName)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Create stderr handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(pretty_formater)

    # Create a file logger
    file_handler = logging.FileHandler("resources/error_list.log", mode="w")
    file_handler.setLevel(level)
    file_handler.setFormatter(pretty_formater)

    # Create JSON file handler
    file_json_handler = logging.handlers.RotatingFileHandler(
        "resources/error_list.jsonl", maxBytes=10000, backupCount=3, mode="w"
    )
    file_json_handler.setLevel(level)
    file_json_formatter = MyJSONFormatter()
    file_json_handler.setFormatter(file_json_formatter)

    # Create QueueListener and attach handlers
    # respect_handler_level is important otherwise the levels of the listeners are ignored!
    queue_listener = logging.handlers.QueueListener(
        log_queue,
        stderr_handler,
        file_json_handler,
        file_handler,
        respect_handler_level=True,
    )

    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(
        logging.WARNING
    )  # Suppress debug messages from third-party libraries
    root_logger.addHandler(
        queue_handler
    )  # Create a separate logger for your application

    app_logger = logger
    app_logger.setLevel(logging.DEBUG)  # Enable debug messages for your app
    app_logger.propagate = False
    app_logger.addHandler(queue_handler)

    # Start the QueueListener
    queue_listener.start()
    atexit.register(queue_listener.stop)


if __name__ == "__main__":
    log_levels = {
        "ERROR": logging.ERROR,
        "WARN": logging.WARN,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }

    address = "localhost"
    port_diac = 61499
    port_opc = 4840
    log_level = log_levels["ERROR"]
    n_samples = 10
    secs_sample = 20
    monitor = [n_samples, secs_sample]
    agent = False

    help_message = (
        "Usage: python core/main.py [ARGS]\n\n"
        " -h, --help: display the help message\n"
        " -a, --address: ip address to bind at (default: localhost)\n"
        " -p, --port_diac: port for the 4diac communication (default: 61499)\n"
        " -u, --port_opc: port for the opc-ua communication (default: 4840)\n"
        " -l, --log_level: logging level at the file resources/error_list.log\n"
        "                  INFO, WARN or ERROR (default: ERROR)\n"
        " -g, --agent: sets on the self-organizing agent\n"
        " -m, --monitor: activates the behavioral anomaly detection feature. \n"
        "       If no parameters are specified, the default values are 10 samples\n"
        "       for the initial training dataset and each sample with 20 seconds. \n"
        "       As an example, you can specify the monitoring parameters in the following way (-m 5 10) \n"
        "       meaning 10 samples for training dataset with 10 seconds of monitoring per sample. \n"
    )

    ## build parser for application command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        metavar="address",
        nargs=1,
        help="ip address to bind at (default: localhost)",
    )
    parser.add_argument(
        "-p",
        metavar="port_diac",
        nargs=1,
        type=int,
        help="port for the 4diac communication (default: 61499)",
    )
    parser.add_argument(
        "-u",
        metavar="port_opc",
        nargs=1,
        type=int,
        help="port for the opc-ua communication (default: 4840)",
    )
    parser.add_argument(
        "-l",
        metavar="log_level",
        nargs=1,
        help="logging level at the file resources/error_list.log, e.g. INFO, WARN or ERROR (default: ERROR)",
    )
    parser.add_argument(
        "-g", action="store_true", help="sets on the self-organizing agent"
    )
    parser.add_argument(
        "-m",
        metavar="monitor",
        nargs="*",
        help="activates the behavioral anomaly detection feature. If no paramters are specified, the default values are 10 samples for initial training, each sample with 20 seconds (approximately 3m20s). As an example, you can specify paramters the following way (-m 5 10) meaning 10 samples for training with 10 seconds each sample.",
    )
    args = parser.parse_args()

    if args.a != None:
        address = args.a[0]
    if args.p != None:
        port_diac = args.p[0]
    if args.u != None:
        port_opc = args.u[0]
    if args.l != None:
        log_level = log_levels[args.l[0]]
    agent = args.g
    if args.m != None:
        if len(args.m) == 2:
            monitor = [int(args.m[0]), int(args.m[1])]
        elif len(args.m) == 1 or len(args.m) > 2:
            print(
                "For the monitoring functionality, please specify 2 arguments or none!"
            )
            exit(2)
    else:
        monitor = None

    ##############################################################
    ## remove all files in monitoring folder
    monitoring_path = os.path.join(
        os.path.dirname(sys.path[0]), "resources", "monitoring", ""
    )
    files = glob.glob("{0}*".format(monitoring_path))
    for f in files:
        os.remove(f)
    ##############################################################

    # Configure the logging output
    setup_logging(log_level)

    # creates the 4diac manager
    m = manager.Manager(monitor=monitor)
    # sets the ua integration option
    m.build_ua_manager_fboot(address, port_opc)

    # creates the tcp server to communicate with the 4diac
    hand = tcp_server.TcpServer(address, port_diac, 10, m)

    try:
        # handles every client
        while True:
            hand.handle_client()
    except KeyboardInterrupt:
        logger.info("interrupted server")
        m.manager_ua.stop_ua()
        hand.stop_server()
        sys.exit(0)
