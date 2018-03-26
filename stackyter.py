#!/usr/bin/env python
"""Run jupyter on a given host and display it localy."""


import os
import sys
import subprocess
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
import yaml
import numpy as np


DEFAULT_CONFIG = os.getenv("HOME") + "/.stackyter-config.yaml"


def string_to_list(a):
    """Transform a string with coma separated values to a list of values."""
    return a if isinstance(a, list) or a is None else a.split(",")


def get_default_config(only_path=False):
    """Get the stackyter default configuration file if it exists."""
    if os.getenv("STACKYTERCONFIG") is not None:  # set up by the user
        config = os.getenv("STACKYTERCONFIG")
        if not os.path.exist(config):
            raise IOError("$STACKYTERCONFIG is defined but the file does "
                          "not exist.")
    elif os.path.exists(DEFAULT_CONFIG):  # default location
        config = DEFAULT_CONFIG
    else:
        return None
    return yaml.load(open(config, 'r')) if not only_path else config


def read_config(config, key=None):
    """Read a config file and return the right configuration."""
    print("INFO: Loading configuration from", config)
    config = yaml.load(open(config, 'r'))
    if key is not None:
        if key in config:
            info_msg = "INFO: Using the '{}' configuration".format(key)
            print(info_msg)
            config = config[key]
        else:
            err_msg = ("Configuration `{}` does not exist. "
                       "Check your default file.").format(key)
            raise IOError(err_msg)

    elif len(config) > 1:
        if 'default_config' in config:
            info_msg = ("INFO: Using default configuration '{}'"
                        .format(config['default_config']))
            print(info_msg)
            config = config[config['default_config']]
        else:
            raise IOError("You must define a 'default_config' "
                          "in you configuration file.")
    else:
        config = config[list(config)[0]]
    return config


def get_config(config, configfile):
    """Get the configuration for stackyter is any."""
    if configfile is None:
        configfile = get_default_config(only_path=True)

    if config is not None:
        # Is there a configuration file?
        if configfile is None:
            raise IOError("No (default) configuration file found or given. "
                          "Check the doc.")
        config = read_config(configfile, key=config)
    elif configfile is not None:
        config = read_config(configfile)
    return config


def setup_parser():
    description = "Run Jupyter on a distant host and display it localy."
    prog = "stackyter.py"
    usage = "{} [options]".format(prog)

    parser = ArgumentParser(prog=prog, usage=usage, description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    # General options
    parser.add_argument(
        '-c', '--config',
        default=None,
        help="Name of the configuration to use, taken from your default "
             "configuration file ($HOME/.stackyter-config.yaml or "
             "$STACKYTERCONFIG). "
             "Default if to use the 'default_config' defined in this file. "
             "The content of the configuration file will be overwritten by "
             "any given command line options.")
    parser.add_argument(
        '-f', '--configfile',
        default=None,
        help="Configuration file containing a set of option values. "
             "The content of this file will be overwritten by any given "
             "command line options.")
    parser.add_argument(
        '-H', "--host",
        default=None,
        help="Name of the target host. Allows you to connect to any host "
             "on which Jupyter is available, or to avoid conflict with the "
             "content of your $HOME/.ssh/config.")
    parser.add_argument(
        '-u', '--username',
        help="Your username on the host. "
             "If not given, ssh will try to figure it out from your "
             "~/.ssh/config or will use your local username.")
    parser.add_argument(
        '-w', "--workdir",
        default=None,
        help="Your working directory on the host.")
    parser.add_argument(
        '-j', "--jupyter",
        default="notebook",
        choices=['notebook', 'lab'],
        help="Either launch a jupyter notebook or a jupyter lab.")
    parser.add_argument(
        "--mysetup",
        default=None,
        help="Path to a setup file (on the host) that will be used to set up "
             "the working environment. A Python installation with Jupyter "
             "must be available to make this work.")
    parser.add_argument(
        "--runbefore",
        default=None,
        help="A list of extra commands to run BEFORE sourcing your setup file."
             " Coma separated for more than one commands, or a list in the "
             "config file.")
    parser.add_argument(
        "--runafter",
        default=None,
        help="A list of extra commands to run AFTER sourcing your setup file."
             " Coma separated for more than one commands, or a list in the "
             "config file.")
    parser.add_argument(
        '-C', '--compression',
        action='store_true',
        default=False,
        help='Activate ssh compression option (-C).')
    parser.add_argument(
        '-S', '--showconfig',
        action='store_true',
        default=False,
        help="Show all available configurations from your default file "
             "and exit.")
    parser.add_argument(
        '-T', '--tensorboard',
        action='store_true',
        default=False,
        help="Lauch an instance of TensorBoard. A Python installation with "
             "TensorFlow must be available to make this work.")
    parser.add_argument(
        '-l', '--logdir',
        default=None,
        help="Absolute path to the TensorBoard log directory. "
             "This is only used if the TensorBoard option is selected.")

    return parser


def main():
    parser = setup_parser()
    args = parser.parse_args()
    default_args = parser.parse_args(args=[])

    # Show available configuration(s) is any and exit
    if args.showconfig:
        config = get_default_config(only_path=True)
        if config is not None:
            config = open(config, 'r')
            print("Your default configuration file contains the following "
                  "configuration(s).")
            print(config.read())
            config.close()
        else:
            print("Error: No default configuration file found.")
        sys.exit(0)

    # Do we have a configuration file
    config = get_config(args.config, args.configfile)
    if config is not None:
        for opt, val in args._get_kwargs():
            # only keep option value from the config file
            # if the user has not set it up from command line
            if opt in config and args.__dict__[opt] == default_args.__dict__[opt]:  # noqa
                setattr(args, opt, config[opt])

    # Do we have a valide host name
    if args.host is None:
        raise ValueError("You must give a valide host name (--host)")

    # Do we have a valid username
    if args.username is not None:
        args.host = "{}@{}".format(args.username, args.host)

    if args.tensorboard:
        if args.logdir is None:
            raise ValueError("You must provide a logdir path to TensorBoard "
                             "(--logdir)")

    # Make sure that we have a list (even empty) for extra commands to run
    if args.runbefore is not None:
        args.runbefore = [run.replace("$", "\$")
                          for run in string_to_list(args.runbefore)]

    if args.runafter is not None:
        args.runafter = [run.replace("$", "\$")
                         for run in string_to_list(args.runafter)]

    # A random port number is selected between 1025 and 65635 (included)
    # for server side to prevent from conflict between users.
    port = np.random.randint(1025, high=65634)
    port_tensorboard = port + 1

    # Start building the command line that will be launched on the host
    cmd_list = []

    # Open the ssh tunnel to the host
    ssh_options = "-"
    ssh_options += "Y"      # Trusted X11 forwarding
    ssh_options += "tt"     # Pseudo terminal allocation = local tty
    if args.compression:
        ssh_options += "C"  # Add compression of all transmitted data

    tunnel = "-L 20001:localhost:{}".format(port)  # Port forwarding

    tunnel2 = ""
    if args.tensorboard:
        tunnel2 = "-L 20002:localhost:{}".format(port_tensorboard)

    ssh_cmd = ("ssh {options} {tunnel} {tunnel2} {host} << EOF"
               .format(options=ssh_options,
                       tunnel=tunnel,
                       tunnel2=tunnel2,
                       host=args.host))

    cmd_list.append(ssh_cmd)

    # Move to the working directory
    if args.workdir is not None:
        cmd_list.append("cd {}".format(args.workdir))

    # Do we have to run something before sourcing the setup file
    if args.runbefore:
        cmd_list.extend(args.runbefore)

    # Use the setup file given by the user to set up the working environment
    if args.mysetup is not None:
        cmd_list.append("source {}".format(args.mysetup))

    # Do we have to run something after sourcing the setup file
    if args.runafter:
        cmd_list.extend(args.runafter)

    # Launch jupyter
    jupyter_cmd = ('jupyter {} --no-browser --port={} --ip=127.0.0.1 &'
                   .format(args.jupyter, port))

    cmd_list.append(jupyter_cmd)

    # Leauch tensorboard
    if args.tensorboard:
        tensorboard_cmd = ('tensorboard --logdir={} --port={} &'
                           .format(args.logdir, port_tensorboard))
        cmd_list.append(tensorboard_cmd)

    # Get the token number and print out the right web page to open
    cmd_list.append("export servers=\`jupyter notebook list\`")

    # If might have to wait a little bit until the server is actually running.
    wait_cmd = ("while [[ \$servers != *'127.0.0.1:{port}'* ]];"
                "do sleep 1;"
                "servers=\`jupyter notebook list\`;"
                "echo waiting...;"
                "done").format(port=port)
    cmd_list.append(wait_cmd)

    server_cmd = ("export servers=\`jupyter notebook list | "
                  "grep '127.0.0.1:{port}'\`").format(port=port)
    cmd_list.append(server_cmd)

    token_cmd = ("export TOKEN=\`echo \$servers | "
                 "sed 's/\//\\n/g' | "
                 "grep token | "
                 "sed 's/ /\\n/g' | "
                 "grep token \`")
    cmd_list.append(token_cmd)

    shellprint_cmd = ("printf '\\n Copy/paste this URL into your browser "
                      "to run the notebook localy "
                      "\n\\x1B[01;92m"
                      "       'http://localhost:20001/\$TOKEN' "
                      "\\x1B[0m\\n\\n'")
    cmd_list.append(shellprint_cmd)
    if args.tensorboard:
        cmd_list.append("printf 'tensorboard"
                        "\\x1B[01;92m"
                        "       'http://localhost:20002/'"
                        "\\x1B[0m\\n\\n'")

    # Go back to the jupyter server
    cmd_list.append('fg')

    # And make sure we can kill it properly
    cmd_list.append("kill -9 `ps | grep jupyter | awk '{print $1}'`")
    if args.tensorboard:
        cmd_list.append("kill -9 `ps | grep tensorboard | awk '{print $1}'`")

    # Close
    cmd_list.append("EOF")

    cmd = '\n'.join(cmd_list)

    # Run jupyter
    subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)


if __name__ == '__main__':
    main()
