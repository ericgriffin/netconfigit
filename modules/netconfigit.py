# -*- coding: utf-8 -*-
"""
Netconfigit and NetworkDevice classes
"""

__license__ = "MIT License"
__author__ = "Eric Griffin"
__copyright__ = "Copyright (C) 2014, Fluent Trade Technologies"
__version__ = "1.1"


import os
import sys
import time
import shutil
import logging
import os.path
import inspect
import threading
import telnetlib
from xml.dom import minidom
from datetime import datetime

import paramiko
from git import *

import aescrypt
import threadpool
from modules import tftpy

# define a global logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Netconfigit(object):
    """Contains configuration data and execution functions for archiving network device configs

    Holds a list of NetworkDevice objects with their associated access information and the jobs to run.
    Holds global configuration information.
    Manages a pool of worker threads used for accessing network devices
    Contains accessory functions related to archiving device configs

    :param config_file: xml configuration file
    :param _password: decryption password
    """

    def __init__(self, config_file, _password):
        """Netconfigit constructor

        Initializes member variables and reads and parses XML configuration file.
        Starts local tftp server and creates temporary directory for holding configs.
        Initializes the device threadpool.

        :param config_file: XML configuration file path
        :param _password: decryption password
        """
        # initialize member variables
        self.device_list = []               # list of device objects defined in the configuration file
        self.device_count = 0               # the number of devices defined in the configuration file
        self.success_list = []              # the list of device actions that have succeeded
        self.failure_list = []                 # the list of device actions that have failed
        self.config = 0                     # the minidom XML configuration data structure
        self.config_devices = 0             # pointer to the device elements in the config minidom structure
        self.tftp_thread = 0                # thread pool for running the local tftp server
        self.device_threadpool = 0          # thread pool for running device actions
        self.password = ""                  # decryption password
        self.verbose = 0                    # verbose logging flag
        self.logfile = "./Netconfigit.log"  # logfile relative path
        self.plaintext_passwords = ""       # boolean value allows use of plaintext passwords in config xml
        self.transfer_ip = ""               # IP address of the local tftp and/or scp server
        self.scp_username = ""              # username used for scp transfer to the local machine
        self.scp_password = ""              # password used for scp transfer to the local machine
        self.scp_chown = ""                 # the group and user to which uploaded files' ownership should be changed
        self.ssh_port = 22                  # port used to ssh to local machine - used by chown
        self.repo_path = ""                 # absolute path to the configuration repository
        self.repo_password = ""             # password for accessing the repository
        self.repository = None              # GitPython repository object
        self.tftp_port = "69"               # port used by local tftp server
        self.tftp_root = ""                 # root directory used by local tftp server
        self.using_git = 0                  # boolean is set to true if the repository directory is a Git repository
        self.tempdir = ".netconfigit/"      # temporary path for downloading configs
        self.time_start = datetime.now()    # starting time timestamp used for calculating total running-time
        self.time_stop = None               # stopping time timestamp used for calculating total running-time
        self.time_timestamp = time.time()               # starting time timestamp

        # formatted timestamp
        self.timestamp = datetime.fromtimestamp(self.time_timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # create the object used for encrypting/decrypting passwords
        self.password = aescrypt.AESCrypt(_password)

        # parse xml configuration file
        self.config = minidom.parse(config_file)
        logging.info("\nUsing %s", config_file)

        # check and load options from XML
        self.options = self.load_options()

        # check existence of devices in configuration
        if self.config.getElementsByTagName('device'):
            self.config_devices = self.config.getElementsByTagName('device')
        else:
            print "\nNo devices specified - quitting"
            exit(1)

        # load devices from XML configuration into device_list
        load_err = self.load_devices_xml()

        if load_err != "0":
            print load_err
            print "Configuration errors detected - quitting"
            exit(1)

        # create temporary directory for receiving configs
        self.tempdir = os.path.dirname(self.tftp_root + self.tempdir)
        try:
            os.stat(self.tempdir)
        except os.error:
            os.mkdir(self.tempdir)
            logger.info("Creating temporary directory " + self.tempdir)

        # initialize the thread used for the local tftp server and start the server
        self.tftp_thread = threadpool.ThreadPool(1)
        self.tftp_thread.add_task(self.tftp_server)

        # initialize the thread pool used by device actions
        logger.info("Creating %s device threads", 20)
        self.device_threadpool = threadpool.ThreadPool(20)

    def run_nc(self):
        """Runs the jobs associated with each device

        Creates a new threaded task for each device.
        """
        # process each device in its own threaded task
        for device in self.device_list:
            self.device_threadpool.add_task(self.process_actions, device)

    def stop_nc(self):
        """Cleans up after the running of all device actions

        Waits until all device threads are finished.
        Copies the configs from the temporary location into the repo location.
        Removes the temporary folder structure.
        """
        # wait until all worker threads are finished
        self.device_threadpool.wait_completion()
        self.tftp_thread.tasks.empty()

        # count downloaded files
        # TODO: count downloaded files

        # copy downloaded files to repo root
        for src_dir, dirs, files in os.walk(self.tempdir):
            dst_dir = src_dir.replace(self.tempdir, self.repo_path)
            if not os.path.exists(dst_dir):
                os.mkdir(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                shutil.move(src_file, dst_dir)

        # delete the temporary directory structure
        try:
            shutil.rmtree(self.tempdir)
        except os.error:
            # wait a few seconds and try again if the OS hasn't released a lock on the folders
            time.sleep(5)
            shutil.rmtree(self.tempdir)

        # Calculate total running-time
        self.time_stop = datetime.now()
        running_time = self.time_stop - self.time_start

        # print results and write them to log file
        with open(self.logfile, "a") as results:
            # print a timestamp and total running time
            results.write("\n-------------------------\n\n")
            print "-------------------------\n"
            print self.timestamp
            results.write(self.timestamp + "\n")
            print "Elapsed time: " + str(running_time)
            results.write("Elapsed Time: " + str(running_time) + "\n\n")

            # completed actions
            print "\nCompleted:"
            results.write("Completed:\n")
            if len(self.success_list) == 0:
                print "\tNONE"
                results.write("\tNONE\n")
            else:
                for success in self.success_list:
                    for success_device, success_action in success.items():
                        print "\t" + success_device + " - " + success_action
                        results.write("\t" + success_device + " - " + success_action + "\n")

            # failed actions
            print "\nFailed:"
            results.write("\nFailed:\n")
            if len(self.failure_list) == 0:
                print "\tNONE"
                results.write("\tNONE\n")
            else:
                for failure in self.failure_list:
                    for failure_device, failure_action in failure.items():
                        print "\t" + failure_device + " - " + failure_action
                        results.write("\t" + failure_device + " - " + failure_action + "\n")

    def load_options(self):
        """Loads options from the XML configuration tree

        :return: err: error code
        """
        err = 0

        # read options from XML
        self.logfile = self.get_element_attribute(self.config, "logging", "path")
        self.plaintext_passwords = self.get_element_attribute(self.config, "passwords", "plaintext")
        self.transfer_ip = self.get_element_attribute(self.config, "transfer", "ip")
        self.scp_username = self.get_element_attribute(self.config, "transfer", "username")
        self.scp_password = self.get_element_attribute(self.config, "transfer", "password")
        self.scp_chown = self.get_element_attribute(self.config, "transfer", "chown")
        self.repo_path = self.get_element_attribute(self.config, "repository", "path")
        self.tftp_port = self.get_element_attribute(self.config, "transfer", "tftp_port")
        self.tftp_root = self.get_element_attribute(self.config, "transfer", "tftp_root")

        # check for existence of repo path and assign it as the tftp server's root
        if self.repo_path != "NULL":
            self.tftp_root = self.repo_path
        else:
            print "Repository path is not specified."
            exit(1)

        # make sure the repo path exists
        if not os.path.isdir(self.repo_path):
            print "Repository path does not exist."
            exit(1)

        # check whether the repo path is under Git control
        git_path_test = self.repo_path + "/.git"
        # .git directory does not exist - not a Git repository
        if not os.path.isdir(git_path_test):
            self.using_git = 0
            logger.warning("%s is not a Git repository", self.repo_path)
        else:
            # repo will be committed/pulled/pushed when everything is done
            self.using_git = 1
            # create a GitPython repository object
            self.repository = Repo(self.repo_path)
            # read the repository password from config xml
            self.repo_password = self.get_element_attribute(self.config, "repository", "password")

            # if repo is under Git try to decode the repo password
            if self.plaintext_passwords != "true" and self.repo_password != "NULL":
                # if repo password ciphertext is invalid length
                if len(self.repo_password) != 24:
                    print "Encrypted repository password must be a multiple of 16 bytes in length."
                    exit(1)
                else:
                    self.repo_password = self.password.decode(self.repo_password)

        # decrypt transfer password
        if self.plaintext_passwords != "true":
            if len(self.scp_password) != 24:
                print "Encrypted transfer password must be a multiple of 16 bytes in length."
                exit(1)
            else:
                self.scp_password = self.password.decode(self.scp_password)

        return err

    def tftp_server(self):
        """Creates and starts a local tftp server

        Creates a TftpServer object and starts it bound to the IP and port of the calling object
        """
        server = tftpy.TftpServer(self.tempdir)
        try:
            logger.info("Starting tftp server on %s:%s with root %s",
                        self.transfer_ip, int(self.tftp_port), self.tempdir)
            server.listen(self.transfer_ip, int(self.tftp_port))
        except tftpy.TftpException, err:
            logger.error("Could not start tftp server on %s:%s with root %s",
                         self.transfer_ip, int(self.tftp_port), self.tempdir)
            logger.error("%s", str(err))
            sys.exit(1)
        except KeyboardInterrupt:
            pass

    @staticmethod
    def get_element_attribute(parent_element, element, attribute):
        """Reads and returns the value of an XML attribute under a given parent node

        :param parent_element: the parent XML element under which to search for the element and attribute
        :param element: the XML element who's attribute will be returned
        :param attribute: the XML attribute who's value will be returned
        :return: retval: the searched attributes value
        """
        retval = "NULL"
        try:
            elements = parent_element.getElementsByTagName(str(element))
        except AttributeError:
            # if element doesn't exist
            return retval
        try:
            for element in elements:
                retval = element.attributes[str(attribute)].value
        except:
            retval = "NULL"
        return retval

    @staticmethod
    def get_all_element_attribute_values(parent_element, element, attribute):
        """Reads and returns a list of matching sub-elements' attribute values from a parent element

        :param parent_element: the parent XML element under which to search
        :param element: the XML element to search for
        :param attribute: the name of the XML attribute which should be added to the list to be returned
        :return: values: list of given attribute values for a given element under the specified parent-element
        """
        values = []
        try:
            elements = parent_element.getElementsByTagName(str(element))
        except AttributeError:
            # if element doesn't exist
            return values
        for element in elements:
            values.append(element.attributes[str(attribute)].value)
        return values

    def load_devices_xml(self):
        """Loads devices and associated data from XML configuration

        Reads XML for device elements and associated data
        Decrypts encrypted passwords in device data
        Checks for errors in the device configuration
        Creates new NetworkDevice objects and populates member variables
        Adds devices to self.device_list
        :return: err: error string
        """
        err = "0"

        for config_device in self.config_devices:
            self.device_count += 1
            #check the name attribute for the device and create a NetworkDevice object
            try:
                # create a new NetworkDevice object
                device = NetworkDevice(config_device.attributes['name'].value)
                device.enabled = config_device.attributes['enabled'].value
            except AttributeError:
                logger.warning("No name attribute for device #%s", str(self.device_count))
                err = "No name attribute for device #" + str(self.device_count)
                continue

            # populate member variables from XML
            device.type = config_device.attributes['type'].value
            device.manufacturer = config_device.attributes['manufacturer'].value
            device.ip = self.get_element_attribute(config_device, "access", "ip")
            device.hostname = self.get_element_attribute(config_device, "access", "hostname")
            device.access_type = self.get_element_attribute(config_device, "access", "type")
            device.port = self.get_element_attribute(config_device, "access", "port")
            device.login_user = self.get_element_attribute(config_device, "access", "username")
            device.login_pass = self.get_element_attribute(config_device, "access", "password")
            device.enable_password = self.get_element_attribute(config_device, "access", "enable")
            device.actions = self.get_all_element_attribute_values(config_device, "action", "type")

            # decrypt passwords
            if self.plaintext_passwords != "true":
                if len(device.login_pass) != 24:
                    print "Encrypted passwords must be a multiple of 16 bytes in length."
                    exit(1)
                else:
                    device.login_pass = self.password.decode(device.login_pass)

                if len(device.enable_password) != 24 and len(device.enable_password) > 4:
                    print "Encrypted passwords must be a multiple of 16 bytes in length."
                    exit(1)
                elif len(device.enable_password) == 24:
                    device.enable_password = self.password.decode(device.enable_password)

            # check for errors in config
            if device.manufacturer == "NULL":
                logger.warning("Must specify device manufacturer for device %s", str(device.name))
                err = "Must specify device manufacturer for device " + str(device.name)
            if device.ip == "NULL" == "NULL":
                logger.warning("Must specify either an IP address or hostname for device %s", str(device.name))
                err = "Must specify either an IP address or hostname for device " + str(device.name)
                continue
            if device.access_type != "ssh" and device.access_type != "telnet":
                logger.warning("Unsupported access type for device %s", str(device.name))
                err = "Unsupported access type for device " + str(device.name)
                continue
            if device.login_user == "NULL" or device.login_pass == "NULL":
                logger.warning("Must supply username and password for device %s", str(device.name))
                err = "Must supply username and password for device " + str(device.name)
                continue

            # add the device to the list of devices
            self.device_list.append(device)
        return err

    def git_commit_push(self):
        """Synchronizes changes with Git repository

        Performs a Git commit with all changes
        Performs a Git pull from origin
        Performs a Git push to origin
        :return: err: error code
        """
        err = 0
        # stage all changes to the commit
        self.repository.git.add(".")

        try:
            # commit the changes to Git
            print self.repository.git.commit('-a', m="Network configuration updates")
            logger.info("Commit completed")
            err = 1
        except:
            logger.warning("No changes to commit to Git")

        try:
            # pause to ensure commit has finished
            time.sleep(5)
            # pull and then push to Git origin
            origin = self.repository.remotes.origin
            origin.pull()
            origin.push()
            print "Git pull-push completed."
        except:
            logger.warning("Could not complete Git pull-push from origin")

        return err

    def chown_config(self, _device, _file):
        """Changes ownership of a file on the local system

        Calls "chown" and assigns user and group defined in config as owner of file passed to function
        :param _device: the device who's config is being chown-ed - to determine absolute file path
        :param _file: the filename who's ownership is changed
        :return: err: error code
        """
        err = 0
        # create an ssh connection to the local machine
        client = paramiko.SSHClient()
        client.get_transport()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.transfer_ip, self.ssh_port, username=self.scp_username, password=self.scp_password)
        chown_command = "chown " + self.scp_chown + ":" + self.scp_chown + " " \
            + self.repo_path + "/" + _device.name + "/" + _file
        logger.info("chown %s with %s", _device.name, self.scp_chown)
        try:
            #issue the chown command
            client.exec_command(chown_command)
        except:
            logger.error("Could not chown %s with %s", _device.name, self.scp_chown)
        return err

    @staticmethod
    def get_ssh_client_channel(_device):
        """Creates an SSH session to a device

        Creates an SSHClient object and initiates the connection
        :param _device: the device
        :return: client, channel: the client session and ssh channel
        """
        client = paramiko.SSHClient()
        client.get_transport()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(_device.ip, port=int(_device.port), username=_device.login_user,
                       password=_device.login_pass, look_for_keys=False)
        channel = client.invoke_shell()
        return client, channel

    def process_actions(self, _device):
        """Processes actions associated with a device

        Adds the modules in the devices subfolder to the path
        Dynamically loads the module defined by the device_manufacturer
        Creates device object for the manufacturer device
        Calls run_action() method for the device object for each action associated with the device
        :param _device: the device
        :return: err: error code
        """
        err = 0
        manufacturer_init = None

        if _device.enabled == "0":
            return err

        # include modules from 'devices' subfolder
        cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(
            inspect.getfile(inspect.currentframe()))[0], "devices")))
        if cmd_subfolder not in sys.path:
            sys.path.insert(0, cmd_subfolder)

        # load the manufacturer module dynamically
        device_class = _device.manufacturer
        try:
            dynamic_module = __import__(device_class)
            # create an object of the manufacturer class dynamically
            manufacturer_init = getattr(dynamic_module, device_class)(_device, self)
        except:
            print "Device manufacturer " + _device.manufacturer + " not implemented."
            err = 1

        if err == 0:
            # run each action for the device
            for action in _device.actions:
                logger.info("Running action %s on %s", action, _device.name)
                run_action = getattr(manufacturer_init, 'run_action')(action)
                # TODO: check returned run_action value to determine whether action succeeded

        return err


class NetworkDevice(threading.Thread):
    """Defines remote access to a network device

    Contains data needed for connecting to and retrieving configs from a network device
    """

    def __init__(self, _name):
        """Class constructor

        :param _name: the name of the device
        """
        threading.Thread.__init__(self)
        self.name = _name               # the name of the device
        self.enabled = "0"              # whether device should be included when netconfigit is run
        self.type = ""                  # type of device (switch, router, etc.) - used by specific implementation
        self.manufacturer = ""          # device manufacturer (cisco, arista, etc.)
        self.ip = ""                    # IP address or hostname of the device
        self.access_type = "ssh"        # method of access used to communicate with the device
        self.port = 22                  # port used in conjunction with access_type
        self.login_user = ""            # device login username
        self.login_pass = ""            # device login password
        self.enable_password = ""       # device enable password
        self.succeeded = 0              # set if device actions succeed after run
        self.actions = []               # list of actions defined in the config associated with the device
