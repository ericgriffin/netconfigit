import logging
import os
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class solace:
    def __init__(self, _device, _netconfigit):
        self.device = _device
        self.netconfigit = _netconfigit

        self.command_copy_current = "copy current-config scp://" + self.netconfigit.scp_username + "@" + self.netconfigit.scp_ip + "/" + self.netconfigit.repo_path + self.device.name + "/current-config\n"


    def run_action(self, action):
        if self.device.access_type == "ssh":
            try:
                self.client, self.channel = self.netconfigit.get_ssh_client_channel(self.device)
            except:
                logger.error("Error connecting to " + self.device.name + "\n")

            if action == "current-config":
                self.get_config()
            else:
                logger.error("Action " + action + " not implemented for Solace devices.\n")

            self.client.close()
        else:
            logger.error("Access method " + self.device.access_type + " not implemented for Solace devices.\n")


    def get_config(self):
        output = ""
        # create the device directory
        self.netconfigit.create_device_directory(self.device)

        time.sleep(10)
        if self.device.enable_password != "NULL":
            self.channel.send("enable\n")
            while not self.channel.recv_ready():
                time.sleep(5)
            output += self.channel.recv(1024)
        self.channel.send(self.command_copy_current)
        while not self.channel.recv_ready():
            time.sleep(10)
        output += self.channel.recv(1024)
        self.channel.send(self.netconfigit.scp_password + "\n")
        while not self.channel.recv_ready():
            time.sleep(5)
        output += self.channel.recv(1024)
        self.channel.send("exit\nexit\n")
        while not self.channel.recv_ready():
            time.sleep(5)
        output += self.channel.recv(1024)
        if self.netconfigit.verbose == 1:
            print output

        return 1