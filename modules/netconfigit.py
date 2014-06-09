import threading
import shutil
from xml.dom import minidom
from git import *
import paramiko
import telnetlib
import logging
import time
from modules import tftpy
import threadpool
import aescrypt
import os
import sys
import os.path
import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class netconfigit():

    devicelist = []
    device_count = 0
    config = 0
    configdevices = 0
    tftp_thread = 0
    device_threadpool = 0
    password = ""
    verbose = 0


    def __init__(self, config_file, _password):
        """

        :param name:
        """
        self.logfile = "./netconfigit.log"
        self.plaintext_passwords = ""
        self.scp_ip = ""
        self.scp_username = ""
        self.scp_password = ""
        self.scp_chown = ""
        self.repo_path = ""
        self.repo_password = ""
        self.repository = ""
        self.tftp_ip = ""
        self.tftp_port = "69"
        self.tftp_root = ""
        self.using_git = 0
        self.tempdir = ".netconfigit/"

        self.password = aescrypt.aescrypt(_password)

        # parse xml configuration file
        self.config = minidom.parse(config_file)
        logging.info("\nUsing %s", config_file)

        # check and load options from XML
        self.options = self.load_options(self.config)
        self.load_options(self.config)

        # check devices
        if self.config.getElementsByTagName('device'):
            self.configdevices = self.config.getElementsByTagName('device')
        else:
            print "\nNo devices specified - quitting"
            exit(1)

        # load devices from XML config into devicelist
        self.devicelist, load_err = self.load_devices_xml(self.configdevices)

        if load_err != "0":
            print load_err
            print "Configuration errors detected - quitting"
            exit(1)

        # create temporary directory for receiving configs
        #self.tempdir = self.tftp_root + self.temporary_storage
        self.tempdir = os.path.dirname(self.tftp_root + self.tempdir)
        try:
            os.stat(self.tempdir)
        except:
            os.mkdir(self.tempdir)
            logger.info("Creating temporary directory " + self.tempdir)

        self.tftp_thread = threadpool.ThreadPool(1)
        self.tftp_thread.add_task(self.tftp_server, self.tftp_ip, int(self.tftp_port), self.tempdir)


    def run_nc(self):
        """


        """
        logger.info("Creating %s device threads", 20)
        self.device_threadpool = threadpool.ThreadPool(20)

        # process devices
        for device in self.devicelist:
            self.device_threadpool.add_task(self.process_actions, device)


    def stop_nc(self):
        """


        """
        self.device_threadpool.wait_completion()
        self.tftp_thread.tasks.empty()

        # count downloaded files


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

        # delete self.tempdir
        try:
            shutil.rmtree(self.tempdir)
        except:
            time.sleep(5)
            shutil.rmtree(self.tempdir)


    def load_options(self, config):
        """

        :param config:
        :return:
        """
        err = 0

        # read options from XML
        self.logfile = self.read_element_attribute(config, "logging", "path")
        self.plaintext_passwords = self.read_element_attribute(config, "passwords", "plaintext")
        self.scp_ip = self.read_element_attribute(config, "transfer", "ip")
        self.scp_username = self.read_element_attribute(config, "transfer", "username")
        self.scp_password = self.read_element_attribute(config, "transfer", "password")
        self.scp_chown = self.read_element_attribute(config, "transfer", "chown")
        self.repo_path = self.read_element_attribute(config, "repository", "path")
        self.tftp_ip = self.read_element_attribute(config, "transfer", "ip")
        self.tftp_port = self.read_element_attribute(config, "transfer", "tftp_port")
        self.tftp_root = self.read_element_attribute(config, "transfer", "tftp_root")

        if self.repo_path != "NULL":
            self.tftp_root = self.repo_path

        # make sure repository exists
        self.repository_git = self.repo_path + "/.git"
        if not os.path.isdir(self.repository_git):
            self.using_git = 0
            logger.warning("%s is not a Git repository", self.repo_path)
        else:
            self.using_git = 1
            self.repository = Repo(self.repo_path)
            self.repo_password = self.read_element_attribute(config, "repository", "password")

            if self.plaintext_passwords != "true":
                # decrypt repo password
                if len(self.repo_password) != 24:
                    print "Encrypted repository password must be a multiple of 16 bytes in length."
                    exit(1)
                else:
                    self.repo_password = self.password.decode(self.repo_password)

        if self.plaintext_passwords != "true":
            # decrypt transfer password
            if len(self.scp_password) != 24:
                print "Encrypted transfer password must be a multiple of 16 bytes in length."
                exit(1)
            else:
                self.scp_password = self.password.decode(self.scp_password)

        return err


    def tftp_server(self, ip, port, root):
        """

        :param ip:
        :param port:
        :param root:
        """

        server = tftpy.TftpServer(root)
        try:
            logger.info("Starting tftp server on %s:%s with root %s", ip, port, root)
            server.listen(ip, port)
        except tftpy.TftpException, err:
            logger.error("Could not start tftp server on %s:%s with root %s", ip, port, root)
            logger.error("%s", str(err))
            sys.exit(1)
        except KeyboardInterrupt:
            pass


    def read_element_attribute(self, parent_element, element, attribute):
        """

        :param parent_element:
        :param element:
        :param attribute:
        :return:
        """
        retval = "NULL"
        try:
            elements = parent_element.getElementsByTagName(str(element))
        except:
            return retval
        try:
            for element in elements:
                retval = element.attributes[str(attribute)].value
        except:
            retval = "NULL"
        return retval


    def read_actions(self, parent_element, element, attribute):
        """

        :param parent_element:
        :param element:
        :param attribute:
        :return:
        """
        actions = []
        try:
            elements = parent_element.getElementsByTagName(str(element))
        except:
            return actions
        try:
            for element in elements:
                actions.append(element.attributes[str(attribute)].value)
        except:
            retval = "NULL"
        return actions


    def load_devices_xml(self, configdevices):
        """

        :param configdevices:
        :return:
        """
        err = "0"

        for configdevice in configdevices:
            self.device_count += 1
            #check the name attribute for the device and create a networkdevice object
            try:
                # create a new networkdevice object
                device = networkdevice(configdevice.attributes['name'].value)
                device.enabled = configdevice.attributes['enabled'].value
            except:
                logger.warning("No name attribute for device #%s", str(self.device_count))
                err = "No name attribute for device #" + str(self.device_count)
                continue

            # populate member variables from XML
            device.type = configdevice.attributes['type'].value
            device.manufacturer = configdevice.attributes['manufacturer'].value
            device.ip = self.read_element_attribute(configdevice, "access", "ip")
            device.hostname = self.read_element_attribute(configdevice, "access", "hostname")
            device.access_type = self.read_element_attribute(configdevice, "access", "type")
            device.port = self.read_element_attribute(configdevice, "access", "port")
            device.login_user = self.read_element_attribute(configdevice, "access", "username")
            device.login_pass = self.read_element_attribute(configdevice, "access", "password")
            device.enable_password = self.read_element_attribute(configdevice, "access", "enable")
            device.actions = self.read_actions(configdevice, "action", "type")

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

            # add the device
            self.devicelist.append(device)

        return self.devicelist, err


    def git_commit_push(self, repo):
        """

        :param repo:
        :return:
        """
        retval = 0
        repo.git.add(".")

        try:
            print repo.git.commit('-a', m="Network configuration updates")
            logger.info("Commit completed")
            retval = 1
        except:
            logger.warning("No changes to commit to Git")

        try:
            time.sleep(5)
            origin = repo.remotes.origin
            origin.pull()
            origin.push()

            print "Git pull-push completed."

        except:
            logger.warning("Could not complete Git pull-push from origin")

        return retval


    def chown_config(self, device, file):
        """

        :param repo:
        :return:
        """
        err = 0
        client = paramiko.SSHClient()
        client.get_transport()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.scp_ip, port="22", username=self.scp_username, password=self.scp_password)
        chowncommand = "chown " + self.scp_chown + ":" + self.scp_chown + " " + self.repo_path + "/" + device.name + "/" + file
        logger.info("Chowning %s with %s", device.name, self.scp_chown)
        try:
            client.exec_command(chowncommand)
        except:
            logger.error("Could not chown %s with %s", device.name, self.scp_chown)
        return err


    def create_device_directory(self, _device):
        """

        :param _device:
        """
        if not os.path.isdir(self.repo_path + _device.name):
            logger.info("Creating directory for %s", _device.name)
            os.mkdir(self.repo_path + _device.name)


    def get_ssh_client_channel(self, _device):
        """

        :param _device:
        :return:
        """
        client = paramiko.SSHClient()
        client.get_transport()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(_device.ip, port=int(_device.port), username=_device.login_user, password=_device.login_pass, look_for_keys=False)
        channel = client.invoke_shell()
        return client, channel


    def process_actions(self, device):

        """

        :param device:
        :return:
        """
        err = 0

        if device.enabled == "0":
            return err

        # include modules from 'devices' subfolder
        cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"devices")))
        if cmd_subfolder not in sys.path:
            sys.path.insert(0, cmd_subfolder)

        # load the manufacturer module dynamically
        device_class = device.manufacturer
        try:
            dynamic_module = __import__(device_class)
            # create an object of the manufacturer class dynamically
            manufacturer_init = getattr(dynamic_module, device_class)(device, self)
        except:
            print "Device manufacturer " + device.manufacturer + " not implemented."
            err = 1

        if err == 0:
            # run each action for the device
            for action in device.actions:
                logger.info("Running action %s on %s", action, device.name)
                run_action = getattr(manufacturer_init, 'run_action')(action)
                #check returned run_action value to determine whether action succeeded

        return err


class networkdevice(threading.Thread):
    """
    contains data needed for connecting to and retrieving configs from a device
    """

    def __init__(self, name):
        """

        :param name:
        """
        threading.Thread.__init__(self)
        self.name = name
        self.enabled = "0"
        self.type = ""
        self.manufacturer = ""
        self.ip = ""
        self.hostname = ""
        self.access_type = "ssh"
        self.port = 22
        self.nbytes = 4096
        self.login_user = ""
        self.login_pass = ""
        self.enable_password = ""
        self.repo = ""
        self.filename = ""
        self.commit = 0
        self.read = 1
        self.succeeded = 0
        self.actions = []

