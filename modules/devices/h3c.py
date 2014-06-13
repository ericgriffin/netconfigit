# -*- coding: utf-8 -*-
"""
Netconfigit H3C device class
"""

__license__ = "MIT License"
__author__ = "Eric Griffin"
__copyright__ = "Copyright (C) 2014, Fluent Trade Technologies"
__version__ = "1.1"


import logging
import os
import time
import telnetlib
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class H3C(object):
    """H3C device class

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
        self.command_copy_startup = "copy startup-config tftp://" + self.netconfigit.transfer_ip + \
                                    "/" + self.device.name + "/startup-config\n"
        self.command_copy_running = "copy running-config tftp://" + self.netconfigit.transfer_ip + \
                                    "/" + self.device.name + "/running-config\n"

    def run_action(self, action):
        """Defines and runs actions for the device associated with the class

        Checks for valid action names and runs the actions
        Returns 0/1 for fail/success of the action
        :param action: the action to run
        """
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

        self.client.read_until('Username:')
        self.client.write(self.device.login_user + "\r")
        self.client.read_until("Password:")
        self.client.write(self.device.login_pass + "\n")
        self.client.write("\r")
        p = self.client.read_eager()
        print p.decode("utf-16")


        output = self.client.read_all().decode("utf-16")
        #print output