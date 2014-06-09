import logging
import os
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class arista:

    def __init__(self, _device, _netconfigit):
        self.device = _device
        self.netconfigit = _netconfigit

        self.command_copy_startup = "copy startup-config tftp://" + self.netconfigit.tftp_ip + "/" + self.device.name + "/startup-config\n"
        self.command_copy_running = "copy running-config tftp://" + self.netconfigit.tftp_ip + "/" + self.device.name + "/running-config\n"


    def run_action(self, action):

        if self.device.access_type == "ssh":
            try:
                self.client, self.channel = self.netconfigit.get_ssh_client_channel(self.device)
            except:
                logger.error("Error connecting to " + self.device.name + "\n")

            if action == "running-config":
                self.get_config("running-config")
            elif action == "startup-config":
                self.get_config("startup-config")
            else:
                logger.error("Action " + action + " not implemented for Arista devices.\n")

            self.client.close()
        else:
            logger.error("Access method " + self.device.access_type + " not implemented for Arista devices.\n")


    def get_config(self, config_type):
        output = ""
        # create the device directory
        self.netconfigit.create_device_directory(self.device)

        time.sleep(5)
        if self.device.enable_password != "NULL":
            self.channel.send("enable\n")
            while not self.channel.recv_ready():
                time.sleep(5)
            output += self.channel.recv(1024)
            self.channel.send(self.device.enable_password + "\n")
            while not self.channel.recv_ready():
                time.sleep(5)
            output += self.channel.recv(1024)
        if config_type == "startup-config":
            self.channel.send(self.command_copy_startup)
        elif config_type == "running-config":
            self.channel.send(self.command_copy_running)
        while not self.channel.recv_ready():
            time.sleep(5)
        output += self.channel.recv(1024)
        if self.netconfigit.verbose == 1:
            print output

        return 1