# -*- coding: utf-8 -*-
"""
Netconfigit Fortinet device class
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


class Fortinet(object):
    """Fortinet device class

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

        self.command_copy_current = "exec backup config tftp " + self.device.name + "/current-config " \
                                    + self.netconfigit.transfer_ip + "\n"
        self.command_clear_dhcp_leases = "execute dhcp lease-clear all" + "\n"

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
                elif action == "clear-dhcp-leases":
                    status = self.clear_dhcp_leases()
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
        """Transfers configurations from device via ssh and tftp

        Issues commands to device via ssh to transfer configs to local tftp server
        :param config_type: the configuration type (ie. startup-config, running-config)
        :return: boolean, 0 means transfer failed, 1 means transfer was successful
        """
        output = ""
        success = 0

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

        if "Send config file to tftp server OK" in output:
            success = 1
        if "Error" in output:
            success = 0

        return success


    def clear_dhcp_leases(self):
        """Clears all DHCP leases
        :return: boolean, 0 means failure, 1 means success
        """
        output = ""
        success = 0
        time.sleep(5)
        self.channel.send(self.command_clear_dhcp_leases)
        while not self.channel.recv_ready():
            time.sleep(5)
        output += self.channel.recv(1024)
        self.channel.send("\n")
        # there is no  output for this command so success is always true
        success = 1
        return success