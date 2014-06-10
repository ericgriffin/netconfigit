#!/usr/bin/env python

# netconfigit
# network device configuration archiver

import sys
import os.path
import signal
import logging
import getopt

from git import *
import paramiko

from modules import netconfigit
from modules import aescrypt


# define a global logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def signal_handler(signal, frame):
    """Handles OS signals

    @rtype : object
    @param signal:
    @param frame:
    """
    sys.exit(0)


def usage(error):
    """Displays command-line argument usage and a specified error message

    :param error: the error message stating what went wrong
    """
    print(error)
    print("\nUsage: %s -c [configuration file] -p [password] (-e [plaintext]) | -d [ciphertext]) (-v)\n" % sys.argv[0])
    exit(0)


# main entry point
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    # global variables
    configuration = ""
    password = ""
    verbose = 0
    opts = ""

    # define command-line flags
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:p:ve:d:")
    except getopt.GetoptError as e:
        print (str(e))
        usage("")

    # determine which flags were called and assign parameters
    for o, a in opts:
        if o == '-c':       # configuration file
            configuration = a
        elif o == '-p':     # decryption password
            password = a
        elif o == '-v':     # verbose output
            verbose = 1
        elif o == '-e':     # encrypt plaintext password given on command-line
            if password == "":
                usage("Encryption password needs to be specified with -p [password]\n")
            input = a
            password = aescrypt.aescrypt(password)
            encoded = password.encode(input)
            print "\nEncrypted form of \"" + input + "\" is:\n" + encoded
            exit(0)
        elif o == '-d':     # decrypt ciphertext password given on command-line
            if password == "":
                usage("Encryption password needs to be specified with -p [password]\n")
            input = a
            password = aescrypt.aescrypt(password)
            decoded = password.decode(input)
            usage("\nDecrypted form of \"" + input + "\" is:\n" + decoded)
        else:
            assert False, "unhandled option"

    # ensure that a password is specified
    if password == "":
        usage("\nNo password specified")

    # ensure that the specified configuration file exists
    if not os.path.isfile(configuration):
        usage("\nConfiguration file %s does not exist - quitting.\n" % configuration)

    # create the neconfigit object
    # the specified configuration file is parsed at this point
    nc = netconfigit.netconfigit(configuration, password)

    # set logging options
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(nc.logfile)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # set verbosity
    if verbose == 1:
        nc.verbose = 1
        paramiko.util.log_to_file(os.path.splitext(nc.logfile)[0] + '_transport.log')

    # run the netconfigit object
    # this initiates the running of the actions specified for each device
    nc.run_nc()

    # here you have the option to do something while the device action threads are running
    while nc.device_threadpool.tasks.unfinished_tasks > 0:
        working = 1

    # initiates the clean-up of the netconfigit run
    # waits for all threads to finish and moves config files
    nc.stop_nc()

    # if repository directory is a git repo, perform a commit/pull/push to synchronize everything
    if nc.using_git == 1:
        nc.git_commit_push(nc.repository)
