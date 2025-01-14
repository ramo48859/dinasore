import importlib
import os
import sys
import xml.etree.ElementTree as ETree
import logging
from data_model_fboot import utils


class FBResources:

    def __init__(self, fb_type):
        self.fb_type = fb_type

        # Gets the dir path to the py and fbt files
        self.root_path = utils.get_fb_files_path(fb_type)
        if "__pycache__" in self.root_path:
            self.root_path = self.root_path.replace('/__pycache__', '')

        # Gets the file path to the python file
        self.py_path = os.path.join(self.root_path, fb_type + '.py')

        # Gets the file path to the fbt (xml) file
        self.fbt_path = os.path.join(self.root_path, fb_type + '.fbt')

    def import_fb(self):
        logging.info('importing fb python file and definition file...')
        root = None
        fb_obj = None

        try:
            concatenate = False
            package = ''
            for dir in self.root_path.split(os.sep):
                if not concatenate:
                    if dir == 'resources':
                        concatenate = True
                if concatenate:
                    package += dir + '.'
            package = package[:-1]
            # Import method from python file
            py_fb = importlib.import_module('.' + self.fb_type, package=package)
            # Gets the running fb method
            fb_class = getattr(py_fb, self.fb_type)
            # Instance the fb class
            fb_obj = fb_class()
            # Reads the xml
            tree = ETree.parse(self.fbt_path)
            # Gets the root element
            root = tree.getroot()

        except ModuleNotFoundError as error:
            logging.error('can not import the module (check fb_type.py nomenclature)')
            logging.error(error)

        except AttributeError as error:
            logging.error('can not find the fb method declaration (check if fb_type.py = def fb_type(...):)')
            logging.error(error)

        except FileNotFoundError as error:
            logging.error('can not find the .fbt file (check .fbt name = fb_type.fbt)')
            logging.error(error)

        except Exception as ex:
            logging.error(ex)

        else:
            logging.info('fb definition (xml) imported from: {0}'.format(self.fbt_path))
            logging.info('python file imported from: {0}'.format(self.py_path))

            # Checking specified data types
            for event in tree.findall('.//Event'):
                if event.get('Type') is not None and event.get('Type') != 'Event':
                    logging.error('Wrong data type "{0}" specified for event {1}'.format(event.get('Type'), event.get('Name')))
                    logging.error('Defaulting to Event')
                    event.set('Type', 'Event')
                
            for varDec in tree.findall('.//VarDeclaration'):
                if varDec.get('Type') is not None and varDec.get('Type') not in utils.UA_TYPES:
                    logging.error('Unknown data type "{0}" assigned to variable {1}'.format(varDec.get('Type'), varDec.get('Name')))
                    logging.error('Defaulting to String')
                    varDec.set('Type', 'String')


        return root, fb_obj

    def get_xml(self):
        logging.info('getting the xml fb definition...')
        root = None

        try:
            # Reads the xml
            tree = ETree.parse(self.fbt_path)
            # Gets the root element
            root = tree.getroot()
        except FileNotFoundError as error:
            logging.error('can not find the .fbt file (check .fbt name = fb_type.fbt)')
            logging.error(error)
        else:
            logging.info('fb definition (xml) imported from: {0}'.format(self.fbt_path))

        return root

    def get_description(self):
        xml_root = self.get_xml()

        # get the id and the type from the xml file
        for iterator in xml_root:
            if iterator.tag == 'SelfDescription':
                dev_id = iterator.attrib['ID']
                dev_type = iterator.attrib['FBType']

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


class GeneralResources:

    def __init__(self):
        # Gets the file path to the python file
        self.fb_path = os.path.join(os.path.dirname(sys.path[0]),
                                    'resources',
                                    'function_blocks')

    def list_existing_fb(self):
        only_files = []

        for f in os.listdir(self.fb_path):
            file_splitted = f.split('.')

            if os.path.isfile(os.path.join(self.fb_path, f)) and \
                    file_splitted[0] not in only_files and \
                    file_splitted[0] != '__init__':

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
