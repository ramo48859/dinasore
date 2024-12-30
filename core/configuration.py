from xml.etree import ElementTree as ETree
import logging
import inspect
from datetime import datetime
import os

from core import fb
from core import fb_interface
from core.fb_resources import FBResources
from data_model_fboot.utils import create_fb_index

logger = logging.getLogger("dinasore")


class Configuration:
    def __init__(self, config_id, config_type, monitor=None):
        self.monitor = monitor

        self.fb_dictionary = dict()

        self.config_id = config_id

        # search function block on file system
        root_fbs_path = os.path.join(os.getcwd(), "resources")
        fb_dict = create_fb_index(root_fbs_path)
        self.fb_dict = fb_dict

        start_resource = FBResources(config_type, fb_dict[config_type])
        self.create_fb("START", start_resource)

    def get_fb(self, fb_name):
        fb_element = None
        try:
            fb_element = self.fb_dictionary[fb_name]
        except KeyError as error:
            logger.error("can not find that fb {0}".format(fb_name))
            logger.error(error)

        return fb_element

    def set_fb(self, fb_name, fb_element):
        self.fb_dictionary[fb_name] = fb_element

    def exists_fb(self, fb_name):
        return fb_name in self.fb_dictionary

    def create_virtualized_fb(self, fb_name, fb_resource: FBResources, ua_update):
        logger.info("creating a virtualized (opc-ua) fb {0}...".format(fb_name))

        self.create_fb(fb_name, fb_resource, monitor=True)
        # sets the ua variables update method
        fb2update = self.get_fb(fb_name)
        fb2update.ua_variables_update = ua_update

    def create_fb(self, fb_name, fb_resource: FBResources, monitor=False):
        logger.info("creating a new fb...")

        exists_fb = fb_resource.exists_fb()
        if not exists_fb:
            # Downloads the fb definition and python code
            logger.info("fb doesnt exists, needs to be downloaded ...")
            fb_resource.download_fb()

        fb_definition, fb_obj = fb_resource.import_fb()

        # check if if happened any importing error
        if fb_definition is not None:
            # Checking order and number or arguments of schedule function
            # Logs warning if order and number are not the same
            scheduleArgs = inspect.getargspec(fb_obj.schedule).args
            if len(scheduleArgs) > 3:
                scheduleArgs = scheduleArgs[3:]
                scheduleArgs = [i.lower() for i in scheduleArgs]
                xmlArgs = []

                for child in fb_definition:
                    # avoid error due to 'VersionInfo' or
                    # 'Identifiction'
                    if child.tag == "InterfaceList":
                        inputvars = child.find("InputVars")
                        varslist = inputvars.findall("VarDeclaration")
                        for xmlVar in varslist:
                            if xmlVar.get("Name") is not None:
                                xmlArgs.append(xmlVar.get("Name").lower())
                            else:
                                logger.error(
                                    'Could not find mandatory "Name" attribute for variable. Please check {0}.fbt'.format(
                                        fb_name
                                    )
                                )

                if scheduleArgs != xmlArgs:
                    logger.warning(
                        "Argument names for schedule function of {0} do not match definition in {0}.fbt".format(
                            fb_name
                        )
                    )
                    logger.warning(
                        "Ensure your variable arguments are the same as the input variables and in the same order"
                    )

            # if it is a real FB, not a hidden one
            if monitor:
                fb_element = fb.FB(fb_name, fb_resource, fb_obj, monitor=self.monitor)
            else:
                fb_element = fb.FB(fb_name, fb_resource, fb_obj)

            self.set_fb(fb_name, fb_element)
            logger.info(
                "created fb type: {0}, instance: {1}".format(
                    fb_resource.fb_type, fb_name
                )
            )
            # returns the both elements
            return fb_element, fb_definition
        else:
            logger.error(
                "can not create the fb type: {0}, instance: {1}".format(
                    fb_resource.fb_type, fb_name
                )
            )
            return None, None

    def create_connection(self, source, destination):
        logger.info("creating a new connection...")

        # Split on last '.' to separate fb name and connection
        source_attr = source.rsplit(sep=".", maxsplit=1)
        destination_attr = destination.rsplit(sep=".", maxsplit=1)

        source_fb = self.get_fb(source_attr[0])
        source_port_name = source_attr[1]
        destination_fb = self.get_fb(destination_attr[0])
        destination_port_name = destination_attr[1]

        connection = fb_interface.Connection(
            destination_fb, destination_port_name, source_fb, source_port_name
        )
        source_fb.add_output_connection(source_port_name, connection)
        destination_fb.add_input_connection(destination_port_name, connection)

        logger.info(
            "connection created between {0} and {1}".format(source, destination)
        )

    def create_watch(self, source, destination):
        logger.info("creating a new watch...")

        source_attr = source.rsplit(sep=".", maxsplit=1)
        source_fb = self.get_fb(source_attr[0])
        source_name = source_attr[1]

        try:
            source_fb.set_attr(source_name, set_watch=True)
        except AttributeError as error:
            # check if the return if None
            logger.error(error)
            logger.error(
                "don't forget to delete the watch when you delete a function block"
            )

        logger.info("watch created between {0} and {1}".format(source, destination))

    def delete_watch(self, source, destination):
        logger.info("deleting a new watch...")

        source_attr = source.split(sep=".")
        source_fb = self.get_fb(source_attr[0])
        source_name = source_attr[1]

        try:
            source_fb.set_attr(source_name, set_watch=False)
        except AttributeError as error:
            # check if the return if None
            logger.error(error)
            logger.error(
                "don't forget to delete the watch when you delete a function block"
            )

        logger.info("watch deleted between {0} and {1}".format(source, destination))

    def write_connection(self, source_value, destination):
        logger.info(f"Writing constant {source_value} to {destination}")
        destination_attr = destination.rsplit(sep=".", maxsplit=1)
        destination_fb = self.get_fb(destination_attr[0])
        destination_name = destination_attr[1]

        v_type, value, is_watch = destination_fb.read_attr(destination_name)

        # Verifies if is to write an event
        if source_value == "$e":
            logger.info("writing an event...")
            if value is not None:
                # If the value is not None increment
                destination_fb.push_event(destination_name, value + 1)
            else:
                # If the value is None push 1
                destination_fb.push_event(destination_name, 1)

        # Writes a hardcoded value
        else:
            logger.info("writing a hardcoded value...")
            value_to_set = self.convert_type(source_value, v_type)
            logger.info(
                f"Data conversion:\n SRC: {source_value}\nType:{v_type}\n Converted value: {value_to_set} DST:{destination_name}"
            )

            destination_fb.set_attr(destination_name, value_to_set)

        logger.info(
            "connection ({0}) configured with the value {1}".format(
                destination, source_value
            )
        )

    def read_watches(self, start_time):
        logger.info("reading watches...")

        resources_xml = ETree.Element("Resource", {"name": self.config_id})

        for fb_name, fb_element in self.fb_dictionary.items():
            fb_xml, watches_len = fb_element.read_watches(start_time)

            if watches_len > 0:
                resources_xml.append(fb_xml)

        fb_watches_len = len(resources_xml.findall("FB"))
        return resources_xml, fb_watches_len

    def start_work(self):
        logger.info("starting the fb flow...")
        for fb_name, fb_element in self.fb_dictionary.items():
            if fb_name != "START":
                fb_element.start()
                # check if the update_variables service is null
                if fb_element.ua_variables_update is not None:
                    # updates the opc-ua variables
                    fb_element.ua_variables_update()

        outputs = self.get_fb("START").fb_obj.schedule()
        self.get_fb("START").update_outputs(outputs)

    def stop_work(self):
        logger.info("stopping the fb flow...")
        for fb_name, fb_element in self.fb_dictionary.items():
            if fb_name != "START":
                fb_element.stop()

    @staticmethod
    def convert_type(value, value_type):
        converted_value = None

        # Unspecified type ANY
        # General format: <Type>#<value>
        # Examples: INT#8500  or FLOAT#41.5
        if value_type == "ANY" or value_type == "DATE_AND_TIME":
            parts = value.split("#")
            if len(parts) == 2:
                value_type, value = parts
            else:
                logger.error(
                    "Incorrect constant formatting! use <Type>#<value> like INT#8500"
                )

        # String variable
        if value_type == "WSTRING" or value_type == "STRING" or value_type == "TIME":
            converted_value = value

        # date and time variable in iso format like: '2011-11-04 00:05:23.283+00:00'
        # Caution!!! if +HH:MM is specified the time zone is clear
        # otherwise the local timeszone is used
        if value_type == "DATE_AND_TIME":
            timestamp = datetime.fromisoformat(value)
            # localize to system timezone if not specified
            if (
                timestamp.tzinfo is None
                or timestamp.tzinfo.utcoffset(timestamp) is None
            ):
                timestamp = timestamp.astimezone()
            converted_value = timestamp

        # Boolean variable
        elif value_type == "BOOL":
            # Checks if is true
            if (
                value == "1"
                or value == "true"
                or value == "True"
                or value == "TRUE"
                or value == "t"
            ):
                converted_value = True
            # Checks if is false
            elif (
                value == "0"
                or value == "false"
                or value == "False"
                or value == "FALSE"
                or value == "f"
            ):
                converted_value = False

        # Integer variable
        elif value_type == "UINT" or value_type == "Event" or value_type == "INT":
            converted_value = int(value)

        # Float variable
        elif value_type == "REAL" or value_type == "LREAL":
            converted_value = float(value)

        return converted_value
