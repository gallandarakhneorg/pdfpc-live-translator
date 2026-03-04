#!/usr/bin/env python3

import os

# Global Constants
VERSION = '1.1'
TRANSPARENCY_LEVEL = 0.7
MODEL_PATH = os.getenv("HOME") + "/vosk-model-en-us"
SOURCE_LANG = 'en'
TARGET_LANG = 'zh'
FONT_SIZE = 40
FONT_COLOR = 'red'
FONT_NAME = 'Arial'
DEFAULT_INPUT_NAME = 'default'
INPUT_BUFFER_SIZE=8192
SOUND_RATE=64000


from argostranslate import package, translate
import argparse
import json
import pyaudio
import re
from screeninfo import get_monitors
import signal
import sys
from tkinter import scrolledtext
import tkinter as tk
from typing import Generator
from vosk import Model, KaldiRecognizer
import wave

class Range(object):
	def __init__(self, scope: str):
		r = re.compile(
			r'^([\[\]]) *([-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?) *'
			r', *([-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?) *([\[\]])$')
		try:
			i = [j for j in re.findall(r, scope)[0]]
			self._start, self._end = float(i[1]), float(i[2])
			if self._start >= self._end:
				raise ArithmeticError
		except (IndexError, ArithmeticError):
			raise SyntaxError("An error occurred with the range provided!")
		self._st = '{}{{}},{{}}{}'.format(i[0], i[3])
		if i[0] == ']':
			if i[3] == ']':
				self._lamba = lambda a, b, c : a < c <= b
			else:
				self._lamba = lambda a, b, c : a < c < b
		else:
			if i[3] == ']':
				self._lamba = lambda a, b, c : a <= c <= b
			else:
				self._lamba = lambda a, b, c : a <= c < b
	    
	def __eq__(self, item: float) -> bool:
		return self._lamba(self._start, self._end, item)

	def __contains__(self, item: float) -> bool:
		return self.__eq__(item)

	def __iter__(self) -> Generator[object, None, None]:
		yield self
	
	def __str__(self) -> str:
		return self._st.format(self._start, self._end)

	def __repr__(self) -> str:
		return self.__str__()



class CliParser(object):
	def __init__(self):
		self._cli_parser = argparse.ArgumentParser("live-translator")
		self._cli_parser.add_argument("--partial", help="enable partial voice recognition", action='store_true')
		self._cli_parser.add_argument("--notranslate", help="avoid live translation", action='store_true')
		self._cli_parser.add_argument("--noui", help="avoid graphical user interface", action='store_true')
		self._cli_parser.add_argument("--quiet", help="avoid live output on the console", action='store_true')
		self._cli_parser.add_argument("--alpha",
			help=f"level of alpha for the background (default: {TRANSPARENCY_LEVEL})",
			default=TRANSPARENCY_LEVEL,
			type=float,
			choices=Range("[0.0, 1.0]"))
		self._cli_parser.add_argument("--langmodel",
			help=f"path to the VOSK language model (default: {MODEL_PATH})",
			default=MODEL_PATH,
			action='store')
		self._cli_parser.add_argument("--source",
			help=f"code of the source language (default: {SOURCE_LANG})",
			default=SOURCE_LANG,
			action='store')
		self._cli_parser.add_argument("--target",
			help=f"code of the target language (default: {TARGET_LANG})",
			default=TARGET_LANG,
			action='store')
		self._cli_parser.add_argument("--height",
			help=f"height of the font to be used (default: {FONT_SIZE})",
			default=FONT_SIZE,
			type=int)
		self._cli_parser.add_argument("--font",
			help=f"name of the font to be used (default: {FONT_NAME})",
			default=FONT_NAME,
			action='store')
		self._cli_parser.add_argument("--color",
			help=f"color of the font to be used (default: {FONT_COLOR})",
			default=FONT_COLOR,
			action='store')
		self._cli_parser.add_argument("--input",
			help=f"index of the input sound device. See --inputs for the list",
			default=-1,
			type=int)
		self._cli_parser.add_argument("--inputs",
			help=f"list the available sound input devices",
			action='store_true')
		self._cli_parser.add_argument("--version",
			help=f"show the version of this tool",
			action='store_true')
		self._cli_parser.add_argument("--screens",
			help=f"list the available screens",
			action='store_true')
		self._cli_parser.add_argument("--screen",
			help=f"number of the screen to be used. See --screens for the list",
			default=-1,
			type=int)
		self._cli_parser.add_argument("--inputbuffersize",
			help=f"size of the audio input buffer (default: {INPUT_BUFFER_SIZE})",
			default=INPUT_BUFFER_SIZE,
			type=int)
		self._cli_parser.add_argument("--soundrate",
			help=f"sound rate (default: {SOUND_RATE})",
			default=SOUND_RATE,
			type=int)
		self._cli_parser.add_argument("--bothlangs",
			help=f"show the source and target messages",
			action='store_true')
		self._cli_args = self._cli_parser.parse_args()

	def args(self) -> object:
		return self._cli_args

	def arg_values(self) -> dict:
		return {
			'alpha': float(self._cli_args.alpha),
			'bothlangs': bool(self._cli_args.bothlangs),
			'color': str(self._cli_args.color),
			'font': str(self._cli_args.font),
			'height': int(self._cli_args.height),
			'input': int(self._cli_args.input),
			'inputs': int(self._cli_args.inputs),
			'inputbuffersize': int(self._cli_args.inputbuffersize),
			'langmodel': str(self._cli_args.langmodel),
			'notranslate': bool(self._cli_args.notranslate),
			'noui': bool(self._cli_args.noui),
			'partial': bool(self._cli_args.partial),
			'quiet': bool(self._cli_args.quiet),
			'screen': str(self._cli_args.screen),
			'screens': str(self._cli_args.screens),
			'soundrate': str(self._cli_args.soundrate),
			'source': str(self._cli_args.source),
			'target': str(self._cli_args.target),
			'version': str(VERSION),
		}

	def __str__(self) -> str:
		return str(self.arg_values())

	def __repr__(self) -> str:
		return self.__str__()



class AudioStreamer(object):
	def __init__(self, cli_args : object):
		self._audio = pyaudio.PyAudio()
		audio_info = self._audio.get_host_api_info_by_index(0)
		numdevices = audio_info.get('deviceCount')
		if cli_args.inputs:
			found_devices = dict()
			for i in range(0, numdevices):
				device = self._audio.get_device_info_by_host_api_device_index(0, i)
				#print(f"{i} - {device.get('index')} - {device.get('name')}")
				if (device.get('maxInputChannels')) > 0:
					found_devices[device.get('index')] = device.get('name')
			print("-------------------------------")
			num_found_devices = len(found_devices)
			print(f"Found {num_found_devices} input devices:")
			for index, name in found_devices.items():
				print(index, " - ", name)
			sys.exit(255)
		else:
			self._index = self.detect_input(cli_args.input)
			if self._index not in range(0, numdevices):
				LOGGER.error(f"Invalid device index {index}")
				sys.exit(255)
			device = self._audio.get_device_info_by_host_api_device_index(0, self._index)
			self._device_name = device.get('name')
			print(f">>>> Selected device {self._index} - " + self._device_name)
			#rate = device.get('defaultSampleRate')
			rate = cli_args.soundrate
			self._stream = self._audio.open(
				format=pyaudio.paInt16, 
				channels=1,
				rate=int(rate),
				input=True,
				frames_per_buffer=8192,
				input_device_index=int(self._index))

	def detect_input(self, number : int) -> int:
		if number < 0:
			audio_info = self._audio.get_host_api_info_by_index(0)
			num_devices = audio_info.get('deviceCount')
			for i in range(0, num_devices):
				device = self._audio.get_device_info_by_host_api_device_index(0, i)
				if (device.get('maxInputChannels')) > 0 and device.get('name') == DEFAULT_INPUT_NAME:
					return device.get('index')
			return 0
		return number

	def stream(self) -> object:
		return self._stream

	def device_index(self) -> int:
		return self._index

	def device_name(self) -> int:
		return self._device_name

	def print_selected_device(self):
		print(f">>>> Input device {self.device_index()} - {self.device_name()}")



class Voice2TextListener(object):
	def update_text(self, text : str):
		pass
		
	def update(self):
		pass
		
	def loop(self):
		pass

	def print_selected_device(self):
		pass



class Voice2TextDisplayer(Voice2TextListener):
	def update_text(self, text : str):
		print(text)



class Translator(object):
	def translate(self, text : str) -> str:
		return text



class MessageBuilder(object):
	def build(self, source : str, target : str) -> str:
		return target



class TwoMessageBuilder(MessageBuilder):
	def build(self, source : str, target : str) -> str:
		return source + " / " + target



class Voice2TextConverter(object):
	def __init__(self, cli_args : object, audio : AudioStreamer, translator : Translator, listener : Voice2TextListener):
		self._partial = cli_args.partial
		self._inputbuffersize = cli_args.inputbuffersize
		self._audio = audio
		self._translator = translator
		self._listener = listener
		if cli_args.bothlangs:
			self._message_builder = TwoMessageBuilder()
		else:
			self._message_builder = MessageBuilder()
		self._model = Model(cli_args.langmodel)
		self._recognizer = KaldiRecognizer(self._model, cli_args.soundrate)
		#self._recognizer.SetWords(True)
		#self._recognizer.SetPartialWords(True)

	def listen_without_partial(self):
		data = self._audio.stream().read(4096, exception_on_overflow=False)
		if self._recognizer.AcceptWaveform(data):
			result = json.loads(self._recognizer.Result())
			if "text" in result:
				if  result["text"]:
					translated = self._message_builder.build(
						result["text"],
						self._translator.translate(result["text"]))
					self._listener.update_text(translated)
		self._listener.update()

	def listen_with_partial(self):
		data = self._audio.stream().read(4096, exception_on_overflow=False)
		if self._recognizer.AcceptWaveform(data):
			result = json.loads(self._recognizer.Result())
			if "text" in result:
				if  result["text"]:
					translated = self._message_builder.build(
						result["text"],
						self._translator.translate(result["text"]))
					self._listener.update_text(translated)
		else:
			partial = json.loads(self._recognizer.PartialResult())
			if "partial" in partial:
				if partial["partial"]:
					translated = self._message_builder.build(
						partial["partial"],
						self._translator.translate(partial["partial"]))
					self._listener.update_text(translated)
		self._listener.update()



class VerboseTranslator(Translator):
	def translate(self, text : str) -> str:
		print(text)
		return text



class AITranslator(Translator):
	def __init__(self, cli_args : object):
		self._from_code = cli_args.source
		self._to_code = cli_args.target
		self._verbose = not cli_args.quiet

	def translate(self, text : str) -> str:
		result = translate.translate(text, self._from_code, self._to_code)
		if self._verbose:
			print(text + " => " + result)
		return result



class TkListener(Voice2TextListener):
	def __init__(self, cli_args : object):
		self._root = tk.Tk()
		self._root.title("Live Translation")

		if cli_args.bothlangs:
			font_height = cli_args.height // 2
		else:
			font_height = cli_args.height

		# Remove the window frame/title bar
		self._root.overrideredirect(True)
		
		# Get screen dimensions
		self._monitor = self.detect_monitor(cli_args.screen)

		# Put the window on screen
		gui_height = cli_args.height * 2
		x = self._monitor.x
		y = self._monitor.y + self._monitor.height - gui_height
		self._root.geometry(f"{self._monitor.width}x{gui_height}+{x}+{y}")

		# Linux (X11/Wayland): use RGBA visual for true transparency
		self._root.wait_visibility(self._root)
		self._root.wm_attributes("-alpha", cli_args.alpha) # Transparent window background
		self._root.wm_attributes("-topmost", True)
		self._root.wm_attributes("-type", "splash") # Force the window to be on top of all other windows
		self._root.config(bg="white")

		# Create the text area
		self._text_area = scrolledtext.ScrolledText(self._root,
			wrap=tk.WORD, 
			width=self._monitor.width, height=gui_height, 
			fg=cli_args.color,
			bd=0, 
			highlightthickness=0, 
			insertbackground="white",
			font=(str(cli_args.font) + " " + str(font_height) + " bold"))
		self._text_area.pack(fill="both", expand=True, padx=10, pady=10)
		self._text_area.tag_configure("center", justify="center")
		self._text_area.insert(tk.END, "Please speak...", "center")

	def show_screen_list():
		monitors = get_monitors()
		for i, monitor in enumerate(monitors):
			print(f"Screen {i+1}:")
			print(f"\tWidth: {monitor.width}")
			print(f"\tHeight: {monitor.height}")
			print(f"\tX: {monitor.x}")
			print(f"\tY: {monitor.y}")
			print(f"\tIs Primary: {monitor.is_primary}")

	def detect_monitor(self, number : int) -> int:
		monitors = get_monitors()
		if number < 0:
			ref_monitor = 0
			for i, monitor in enumerate(monitors):
				if monitor.is_primary:
					return monitor
				if monitor.x == 0:
					ref_monitor = monitor
			return ref_monitor
		for i, monitor in enumerate(monitors):
			if i == number:
				return monitor
		print(f"Unable to detect the screen {number}")
		sys.exit(255)

	def print_selected_device(self):
		monitor = self.get_monitor()
		print(f">>>> Screen ({monitor.x},{monitor.y})({monitor.width}x{monitor.height}) - {monitor.name}")

	def get_monitor(self):
		return self._monitor

	def get_window(self):
		return self._root
	
	def get_text_area(self):
		return self._text_area

	def update_text(self, text):
		self._text_area.delete(1.0, tk.END)
		self._text_area.insert(tk.END, text, "center")

	def update(self):
		self._root.update()

	def loop(self):
		self._root.mainloop()


def main():
	cli_args = CliParser().args()
	if cli_args.version:
		print(f"v{VERSION}")
		sys.exit(255)
	if cli_args.screens:
		TkListener.show_screen_list()
		sys.exit(255)
	
	print("# AUDIO ###################################")
	audio = AudioStreamer(cli_args)

	print("# UI INIT #################################")
	if cli_args.noui:
		print("Initiate the console interface")
		ui = Voice2TextDisplayer()
	else:
		print("Initiate the Tk interface")
		ui = TkListener(cli_args)

	print("# TRANSLATOR ##############################")
	if cli_args.notranslate:
		if cli_args.quiet:
			print("No translator; be quiet")
			translator = Translator()
		else:
			print("No translator; be verbose")
			translator = VerboseTranslator()
	else:
		print(f"Translate from {cli_args.source} to {cli_args.target}")
		translator = AITranslator(cli_args)

	print("# VOICE 2 TEXT ############################")
	v2t = Voice2TextConverter(cli_args, audio, translator, ui)

	print("# LISTENING ###############################")
	audio.print_selected_device()
	ui.print_selected_device()
	if cli_args.partial:
		while True:
			v2t.listen_with_partial()
	else:
		while True:
			v2t.listen_without_partial()
	ui.loop()



if __name__ == '__main__':
	main()
	
