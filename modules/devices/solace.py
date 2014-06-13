# -*- coding: utf-8 -*-
"""
Netconfigit Solace device class
"""

__license__ = "MIT License"
__author__ = "Eric Griffin"
__copyright__ = "Copyright (C) 2014, Fluent Trade Technologies"
__version__ = "1.1"


import logging
import os
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class solace(object):
    """Solace Systems device class

    Defines and runs device-specific actions on a device
    :param _device: the device
    :param _netconfigit: the netconfigit object containing the configuration
    """

    def __init__(self, _device, _netconfigit):
        """Defines action commands for the device associated with the class

        :param _device: the device on which actions are being run
        :param _netconfigit: the netconfigit object containing the configuration
        """
        self.device = _device
        self.netconfigit = _netconfigit

        self.command_copy_current = "copy current-config scp://" + self.netconfigit.scp_username + "@" + \
                                    self.netconfigit.transfer_ip + "/" + self.netconfigit.repo_path + \
                                    self.device.name + "/current-config\n"

    def run_action(self, action):
        """Defines and runs actions for the device associated with the class

        Checks for valid action names and runs the actions
        Returns 0/1 for fail/success of the action
        :param action: the action to run
        """
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