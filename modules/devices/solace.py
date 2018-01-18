# -*- coding: utf-8 -*-
"""
Netconfigit Solace device class
"""

import logging
import os
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Solace(object):
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
        status = 0
        connected = 0

        if self.device.access_type == "ssh":
            try:
                self.client, self.channel = self.netconfigit.get_ssh_client_channel(self.device)
                connected = 1
            except:
                logger.error("Error connecting to " + self.device.name)

            if connected == 1:
                if action == "current-config":
                    status = self.get_config()
                else:
                    logger.error("Action " + action + " not implemented for " +
                                 self.device.manufacturer.title() + " devices.")
                self.client.close()
        else:
            logger.error("Access method " + self.device.access_type + " not implemented for " +
                         self.device.manufacturer.title() + " devices.")

        if status == 1:
            self.netconfigit.success_list.append({self.device.name: action})
        if status == 0:
            self.netconfigit.failure_list.append({self.device.name: action})

    def get_config(self):
        """Transfers configurations from device via ssh and scp

        Issues commands to device via ssh to transfer configs to local scp server
        :param config_type: the configuration type (ie. startup-config, running-config)
        :return: boolean, 0 means transfer failed, 1 means transfer was successful
        """
        output = ""
        success = 0

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

        if "bytes copied" in output:
            success = 1
        if "Error" in output:
            success = 0

        return success