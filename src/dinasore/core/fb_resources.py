import importlib
import os
import sys
import xml.etree.ElementTree as ETree
import logging
from pathlib import Path
from dinasore.data_model_fboot import utils
from typing import List, Dict

from time import perf_counter

logger = logging.getLogger("dinasore")


class FBResources:
    def __init__(self, fb_type: str, py_path: Path, fbt_path: Path, search_path: Path):
        # type(name) of function block
        self.fb_type = fb_type

        # Gets the file path to the python file
        self.py_path = py_path

        # Gets the file path to the fbt (xml) file
        self.fbt_path = fbt_path

        # Path, which is added to the python path on import
        self.search_path = search_path

        # module name relative to the search path
        module_path = str(py_path.relative_to(search_path))
        self.module_name = module_path.replace(os.sep, ".").rstrip(".py")

        self.xml_tree = None

    def import_fb(self):
        logger.info("importing fb python file and definition file...")
        root = None
        fb_obj = None

        # add search path to python path if not already there
        if str(self.search_path) not in sys.path:
            sys.path.append(str(self.search_path))

        try:
            # Import method from python file
            start = perf_counter()
            self.py_fb = importlib.import_module(self.module_name)
            # sys.path.pop(0)
            end = perf_counter()
            logger.info(f"import_time: {end-start}")
            # Gets the running fb method
            fb_class = getattr(self.py_fb, self.fb_type)
            # Instance the fb class
            fb_obj = fb_class()

            # Loads the xml function block definition from disk
            self.xml_tree = self._fetch_xml()
            # Gets the root element
            root = self.xml_tree.getroot()

        except ModuleNotFoundError as error:
            logger.error("can not import the module (check fb_type.py nomenclature)")
            logger.error(error)

        except AttributeError as error:
            logger.error(
                "can not find the fb method declaration (check if fb_type.py = def fb_type(...):)"
            )
            logger.error(error)

        except FileNotFoundError as error:
            logger.error("can not find the .fbt file (check .fbt name = fb_type.fbt)")
            logger.error(error)

        except Exception as ex:
            logger.error(ex)

        else:
            logger.info("fb definition (xml) imported from: {0}".format(self.fbt_path))
            logger.info("python file imported from: {0}".format(self.py_path))

            # Checking specified data types
            for event in self.xml_tree.findall(".//Event"):
                if event.get("Type") is not None and event.get("Type") != "Event":
                    logger.error(
                        'Wrong data type "{0}" specified for event {1}'.format(
                            event.get("Type"), event.get("Name")
                        )
                    )
                    logger.error("Defaulting to Event")
                    event.set("Type", "Event")

            for varDec in self.xml_tree.findall(".//VarDeclaration"):
                if (
                    varDec.get("Type") is not None
                    and varDec.get("Type") not in utils.XML_4DIAC
                ):
                    logger.error(
                        'Unknown data type "{0}" assigned to variable {1}'.format(
                            varDec.get("Type"), varDec.get("Name")
                        )
                    )
                    logger.error("Defaulting to String")
                    varDec.set("Type", "String")

        return root, fb_obj

    def reload(self):
        importlib.reload(self.py_fb)
        # Gets the running fb method
        fb_class = getattr(self.py_fb, self.fb_type)
        # Instance the fb class
        return fb_class()

    def _fetch_xml(self):
        logger.info("getting the xml fb definition...")
        tree = None

        try:
            # Reads the xml
            tree = ETree.parse(self.fbt_path)
        except FileNotFoundError as error:
            logger.error("can not find the .fbt file (check .fbt name = fb_type.fbt)")
            logger.error(error)
        else:
            logger.info("fb definition (xml) imported from: {0}".format(self.fbt_path))

        return tree

    def get_xml(self):
        if self.xml_tree is None:
            self.xml_tree = self._fetch_xml()
        return self.xml_tree

    def get_description(self):
        xml_root = self.get_xml()

        # get the id and the type from the xml file
        for iterator in xml_root:
            if iterator.tag == "SelfDescription":
                dev_id = iterator.attrib["ID"]
                dev_type = iterator.attrib["FBType"]

                return dev_id, dev_type

    def exists_fb(self):
        # Verifies if exists the python file
        exists_py = os.path.isfile(self.py_path)
        # Verifies if exists the fbt file
        exists_fbt = os.path.isfile(self.fbt_path)

        if exists_py and exists_fbt:
            return True
        else:
            return False

    def download_fb(self):
        pass

    def exists_module(self, mod_id):
        pass

    def download_module(self, mod_id):
        pass


def search_fbs(root_directories: List[Path]) -> Dict[str, FBResources]:
    # Find all .fbt files
    fb_index: Dict[str, FBResources] = {}
    for d in root_directories:
        fbt_files = list(d.rglob("*.fbt"))
        # root directory needs to be in the python path to find the modules later

        for fbt_file in fbt_files:
            # Convert fbt_file to a Path object (if it isn't already)
            fbt_file = Path(fbt_file)

            # Get directory name and file name
            dir_name = fbt_file.parent
            fbt_file_name = fbt_file.name

            # Derive fb_type and py_file
            fb_type = fbt_file_name.replace(".fbt", "")
            py_file = dir_name.joinpath(fbt_file_name.replace(".fbt", ".py"))
            # Check if the corresponding .py file exists
            if py_file.exists():
                fb_index[fb_type] = FBResources(fb_type, py_file, fbt_file, d)
            else:
                logger.warning(
                    f"Discovered {py_file} but not its corresponding Python implementation *.py"
                )
    return fb_index


class GeneralResources:
    def __init__(self):
        # Gets the file path to the python file
        self.fb_path = os.path.join(
            os.path.dirname(sys.path[0]), "resources", "function_blocks"
        )

    def list_existing_fb(self):
        only_files = []

        for f in os.listdir(self.fb_path):
            file_splitted = f.split(".")

            if (
                os.path.isfile(os.path.join(self.fb_path, f))
                and file_splitted[0] not in only_files
                and file_splitted[0] != "__init__"
            ):
                only_files.append(file_splitted[0])

        return only_files

    def search_description(self, dev_id):
        fb_types = self.list_existing_fb()

        for fb_type in fb_types:
            fb = FBResources(fb_type)
            # gets the device id and type
            dev_id_iterator, dev_type = fb.get_description()

            # compares if matches with the dev_id
            if dev_id == dev_id_iterator:
                return fb_type
