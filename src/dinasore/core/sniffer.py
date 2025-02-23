import threading
import datetime
import logging

from dinasore.core.fb_resources import FBResources


# This sniffer class looks for changes in the function block functions

logger = logging.getLogger("dinasore")


class Sniffer(threading.Thread):
    def __init__(self, fb_resource: FBResources, message_queue):
        threading.Thread.__init__(self, name=fb_resource.fb_type)
        self.alive = True
        self.fb_resource = fb_resource
        self.message_queue = message_queue

        self.mtime = datetime.datetime.fromtimestamp(
            fb_resource.py_path.stat().st_mtime
        )

    def run(self):
        logger.info(
            "Sniffer for {0} has been activated".format(self.fb_resource.fb_type)
        )
        while self.alive:
            nmtime = datetime.datetime.fromtimestamp(
                self.fb_resource.py_path.stat().st_mtime
            )
            if nmtime > self.mtime:
                self.mtime = nmtime
                # Send new object to fb thread
                self.message_queue.put(self.fb_resource.reload())
                logger.info(
                    "Changes to {0} detected, updating".format(
                        self.fb_resource.fb_type + ".py"
                    )
                )

    def kill(self):
        self.alive = False
