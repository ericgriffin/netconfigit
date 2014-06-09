import logging
import os
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class fortinet:

    def __init__(self, _device, _netconfigit):
        self.device = _device
        self.netconfigit = _netconfigit

        self.command_copy_current = "exec backup config tftp " + self.device.name + "/current-config " + self.netconfigit.tftp_ip + "\n"


    def run_action(self, action):
        if self.device.access_type == "ssh":
            try:
                self.client, self.channel = self.netconfigit.get_ssh_client_channel(self.device)
            except:
                logger.error("Error connecting to " + self.device.name + "\n")

            if action == "current-config":
                self.get_config()
            else:
                logger.error("Action " + action + " not implemented for Fortinet devices.\n")

            self.client.close()
        else:
            logger.error("Access method " + self.device.access_type + " not implemented for Fortinet devices.\n")


    def get_config(self):
        output = ""
        # create the device directory
        self.netconfigit.create_device_directory(self.device)

        time.sleep(5)
        self.channel.send(self.command_copy_current)
        while not self.channel.recv_ready():
            time.sleep(7)
        output += self.channel.recv(1024)
        self.channel.send("\n")
        while not self.channel.recv_ready():
            time.sleep(12)
        output += self.channel.recv(1024)
        if self.netconfigit.verbose == 1:
            print output

        return 1