#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import time

DIR = os.getcwd()

def which_command(command : str) -> str:
	# Get the PATH environment variable
	path = os.getenv("PATH")
	if not path:
		return str(command)
	# Split PATH into individual directories
	path_dirs = path.split(os.pathsep)
	# Check for the command in each directory
	for dir in path_dirs:
		candidate = os.path.join(dir, command)
		if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
			return str(candidate)
	return str(command)
    
    
    
def parse_cli_arguments() -> object:
	cli_parser = argparse.ArgumentParser("start_talk_translate")
	cli_parser.add_argument("--partial", help="enable partial voice recognition", action='store_true')
	cli_parser.add_argument("--notranslate", help="avoid live translation", action='store_true')
	cli_parser.add_argument("--quiet", help="avoid live output on the console", action='store_true')
	cli_parser.add_argument("--langmodel",
		help=f"path to the VOSK language model",
		action='store')
	cli_parser.add_argument("--pythonenv",
		help=f"path to Python virtual environment",
		action='store')
	cli_parser.add_argument("--input",
		help=f"index of the input sound device. See --inputs for the list",
		default=-1,
		type=int)
	cli_parser.add_argument("--inputs",
		help=f"list the available sound input devices",
		action='store_true')
	cli_parser.add_argument("--screens",
		help=f"list the available screens",
		action='store_true')
	cli_parser.add_argument("--screen",
		help=f"number of the screen to be used. See --screens for the list",
		default=-1,
		type=int)
	cli_parser.add_argument("--single", "-S", help="Force to use only one screen", action='store_true')
	cli_parser.add_argument("--swap", "-s", help="swap the presentation/presenter screens", action='store_true')
	cli_parser.add_argument("--delay",
		help=f"delay between pdfpc launch and the overlay launch (default: 2s)",
		default=2,
		type=int)
	cli_parser.add_argument("--page", "-P", help="start the talk at the given page number (default: 1)",
		default=1,
		type=int)
	#return cli_parser.parse_args()
	return cli_parser.parse_known_args()


def read_user_config(cli_args : object):
	global V2T_MODEL_PATH
	global V2T_VIRTUAL_ENV

	V2T_MODEL_PATH = None
	V2T_VIRTUAL_ENV = None

	# User configuration file
	# Must contain the variable definition for V2T_MODEL_PATH and V2T_VIRTUAL_ENV
	config_path = Path.home() / ".afcrc"
	if config_path.exists():
		# Source the configuration file (emulate bash sourcing)
		with open(config_path, "r") as f:
			for line in f:
				match = re.search(r'V2T_MODEL_PATH=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line)
				if match:
					V2T_MODEL_PATH = match.group(1)
				else:
					match = re.search(r'V2T_VIRTUAL_ENV=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line)
					if match:
						V2T_VIRTUAL_ENV = match.group(1)
	if not V2T_MODEL_PATH:
		V2T_MODEL_PATH = cli_args.langmodel

	if not V2T_VIRTUAL_ENV:
		V2T_VIRTUAL_ENV = cli_args.pythonenv

	if not V2T_MODEL_PATH or not V2T_VIRTUAL_ENV:
		print("V2T_MODEL_PATH or V2T_VIRTUAL_ENV not set in .afcrc or from command line")
		sys.exit(255)


# Launch pdfpc in the background
def launch_pdfpc(cli_arguments : object, extra_arguments : list) -> object:
	if cli_arguments.inputs or cli_arguments.screens:
		return None
	pdfpc_bin = which_command("pdfpc")
	arguments = list([pdfpc_bin, "-w", "none", "-P", str(cli_arguments.page)])
	if cli_arguments.single:
		arguments.append("-S")
	if cli_arguments.swap:
		arguments.append("-s")
	arguments = arguments + list(extra_arguments)
	pdfpc_process = subprocess.Popen(arguments)
	return pdfpc_process


# Launch the Tkinter overlay
def launch_overlay(cli_arguments : object) -> object:
	arguments = list([
		f"{V2T_VIRTUAL_ENV}/bin/python3", f"{DIR}/live-translator.py", 
		"--langmodel",  V2T_MODEL_PATH])
	if cli_arguments.partial:
		arguments.append("--partial")
	if cli_arguments.notranslate:
		arguments.append("--notranslate")
	if cli_arguments.quiet:
		arguments.append("--quiet")
	if cli_arguments.inputs:
		arguments.append("--inputs")
	if cli_arguments.screens:
		arguments.append("--screens")
	if cli_arguments.input >= 0:
		arguments.append("--input")
		arguments.append(str(cli_arguments.input))
	if cli_arguments.screen >= 0:
		arguments.append("--screen")
		arguments.append(str(cli_arguments.screen))
	overlay_process = subprocess.Popen(arguments)
	return overlay_process


cli_arguments, extra_arguments = parse_cli_arguments()
read_user_config(cli_arguments)
pdfpc_process = launch_pdfpc(cli_arguments, extra_arguments)
# Give pdfpc time to open and go fullscreen
time.sleep(int(cli_arguments.delay))
overlay_process = launch_overlay(cli_arguments)

if pdfpc_process:
	# Wait for pdfpc to exit, then kill the overlay too
	pdfpc_process.wait()
	overlay_process.terminate()
else:
	# Wait for overlay to exit
	overlay_process.wait()

