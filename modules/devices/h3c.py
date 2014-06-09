import logging
import os
import time
import telnetlib
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class h3c:

    def __init__(self, _device, _netconfigit):
        self.device = _device
        self.netconfigit = _netconfigit
        self.command_copy_startup = "copy startup-config tftp://" + self.netconfigit.tftp_ip + "/" + self.device.name + "/startup-config\n"
        self.command_copy_running = "copy running-config tftp://" + self.netconfigit.tftp_ip + "/" + self.device.name + "/running-config\n"


    def run_action(self, action):

        if self.device.access_type == "telnet":
            try:
                self.client = telnetlib.Telnet(self.device.ip)
            except:
                logger.error("Error connecting to " + self.device.name + "\n")

            if action == "startup-config":
                self.get_config("startup-config")
            else:
                logger.error("Action " + action + " not implemented for H3C devices.\n")

            self.client.close()
        else:
            logger.error("Access method " + self.device.access_type + " not implemented for H3C devices.\n")


    def get_config(self, config_type):
        output = ""
        # create the device directory
        self.netconfigit.create_device_directory(self.device)
        self.client.read_until('Username:')
        self.client.write(self.device.login_user + "\r")
        self.client.read_until("Password:")
        self.client.write(self.device.login_pass + "\n")
        self.client.write("\r")
        p = self.client.read_eager()
        print p.decode("utf-16")


        output = self.client.read_all().decode("utf-16")
        #print output