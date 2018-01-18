# -*- coding: utf-8 -*-
"""
Netconfigit H3C device class
"""

import logging
import os
import time
import shutil
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
        self.command_copy_startup = "backup startup-configuration to " + self.netconfigit.transfer_ip + \
                                    " " + self.device.name + ".cfg\n"

    def run_action(self, action):
        """Defines and runs actions for the device associated with the class

        Checks for valid action names and runs the actions
        Returns 0/1 for fail/success of the action
        :param action: the action to run
        """
        status = 0
        connected = 0

        if self.device.access_type == "telnet":
            try:
                self.client = telnetlib.Telnet(self.device.ip)
                connected = 1
            except:
                logger.error("Error connecting to " + self.device.name)

            if connected == 1:
                if action == "startup-config":
                    status = self.get_config_telnet()
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

    def get_config_telnet(self):
        """Transfers configurations from device via telnet and tftp

        Issues commands to device via telnet to transfer configs to local tftp server
        :return: boolean, 0 means transfer failed, 1 means transfer was successful
        """
        output = ""
        success = 0
        self.client.write("vt100".encode('ascii') + "\n\r".encode('ascii'))
        self.client.read_until('Username:')
        self.client.write(self.device.login_user.encode('ascii') + "\n\r".encode('ascii'))
        self.client.read_until("Password:")
        self.client.write(self.device.login_pass.encode('ascii') + "\n\r".encode('ascii'))
        self.client.read_until(">")
        self.client.write(self.command_copy_startup.encode('ascii'))
        self.client.write("quit\n\r".encode('ascii'))
        output = self.client.read_all()

        if self.netconfigit.verbose == 1:
            print output

        if "finished!" in output:
            success = 1
            # H3C can't specify directory for tftp download
            # move the downloaded file to the named subdirectory in the temporary directory
            dst_dir = self.netconfigit.tempdir + "/" + self.device.name
            src_file = dst_dir + ".cfg"
            dst_file = dst_dir + "/" + "startup-configuration.cfg"
            # make the named subfolder if it doesn't exist
            if not os.path.exists(dst_dir):
                os.mkdir(dst_dir)
            # rename and move the downloaded file from the temporary directory root to the named subfolder
            shutil.move(src_file, dst_dir)
            os.rename(dst_dir + "/" + self.device.name + ".cfg", dst_file)
        else:
            success = 0

        return success