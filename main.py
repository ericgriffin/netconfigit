#!/usr/bin/python

import os, sys
import os.path
import time
import threading
import signal
from xml.dom import minidom
import getopt
from modules import tftpy
from git import *
import paramiko
from modules import threadpool
import logging
from modules import netconfigit
from modules import aescrypt


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def signal_handler(signal, frame):
    """


    @rtype : object
    @param signal:
    @param frame:
    """
    sys.exit(0)


def usage(error):
    """

    :param error:
    """
    print(error)
    print("\nUsage: %s -c [configuration file] -p [password] (-e [plaintext]) | -d [ciphertext]) (-v)\n" % sys.argv[0])
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    configuration = ""
    password = ""
    verbose = 0
    opts = ""

    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:p:ve:d:")
    except getopt.GetoptError as e:
        print (str(e))
        usage()

    for o, a in opts:
        if o == '-c':
            configuration = a
        elif o == '-p':
            password = a
        elif o == '-v':
            verbose = 1
        elif o == '-e':
            if password == "":
                usage("Encryption password needs to be specified with -p [password]\n")
            input = a
            password = aescrypt.aescrypt(password)
            encoded = password.encode(input)
            print "\nEncrypted form of \"" + input + "\" is:\n" + encoded
            exit(0)
        elif o == '-d':
            if password == "":
                usage("Encryption password needs to be specified with -p [password]\n")
            input = a
            password = aescrypt.aescrypt(password)
            decoded = password.decode(input)
            usage("\nDecrypted form of \"" + input + "\" is:\n" + decoded)
        else:
            assert False, "unhandled option"

    # check command-line syntax
    if password == "":
        usage("\nNo password specified")

    # make sure configuration file exists
    if not os.path.isfile(configuration):
        usage("\nConfiguration file %s does not exist - quitting.\n" % configuration)

    nc = netconfigit.netconfigit(configuration, password)

    if verbose == 1:
        nc.verbose = 1

    # set logging options
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(nc.logfile)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if nc.verbose == 1:
        paramiko.util.log_to_file(os.path.splitext(nc.logfile)[0] + '_transport.log')

    nc.run_nc()

    #while nc.device_threadpool.tasks.unfinished_tasks > 0:
    #    print "working..."

    nc.stop_nc()

    if nc.using_git == 1:
        nc.git_commit_push(nc.repository)


