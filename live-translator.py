import pyaudio
import wave
import json
import argparse

from vosk import Model, KaldiRecognizer

from argostranslate import package, translate

import tkinter as tk
from tkinter import scrolledtext

# Configuration
gui_font_size = 40
gui_height = gui_font_size * 2
gui_font = "Arial"
gui_color = "red"
transparency_level = 0.7
model_path = "/path/to/vosk-model-en-us-0.42-gigaspeech"
from_code = "en"
to_code = "zh"

# Command line arguments
cli_parser = argparse.ArgumentParser("live-translator")
cli_parser.add_argument("--nopartial", help="Avoid partial voice recognition.", action='store_true')
cli_parser.add_argument("--notranslate", help="Avoid live translation.", action='store_true')
cli_parser.add_argument("--quiet", help="Avoid live output on the console.", action='store_true')
cli_args = cli_parser.parse_args()

# Initialize VOSK
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)
#recognizer.SetWords(True)
#recognizer.SetPartialWords(True)

# Audio setup
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
if not cli_args.quiet:
	audio_info = p.get_host_api_info_by_index(0)
	numdevices = audio_info.get('deviceCount')
	for i in range(0, numdevices):
		if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
			print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

# GUI setup

def create_ui():
	root = tk.Tk()
	root.title("Live Translation")
	
	# Remove the window frame/title bar
	root.overrideredirect(True)
	
	# Get screen dimensions
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()

	# Put the window on screen
	x = 0
	y = screen_height - gui_height
	root.geometry(f"{screen_width}x{gui_height}+{x}+{y}")

	# Linux (X11/Wayland): use RGBA visual for true transparency
	root.wait_visibility(root)
	root.wm_attributes("-alpha", transparency_level) # Transparent window background
	root.wm_attributes("-topmost", True)
	root.wm_attributes("-type", "splash") # Force the window to be on top of all other windows
	root.config(bg="white")

	# Create the text area
	text_area = scrolledtext.ScrolledText(root,
		wrap=tk.WORD, 
		width=screen_width, height=gui_height, 
		fg=gui_color,
		bd=0, 
		highlightthickness=0, 
		insertbackground="white",
		font=(str(gui_font) + " " + str(gui_font_size) + " bold"))
	text_area.pack(fill="both", expand=True, padx=10, pady=10)
	text_area.tag_configure("center", justify="center")
	
	return (root, text_area)


def update_text(text_area, text):
	text_area.delete(1.0, tk.END)
	text_area.insert(tk.END, text, "center")

def do_translate(text):
	if cli_args.notranslate:
		result = text
		if not cli_args.quiet:
			print(text + " => " + result)
	else:
		result = translate.translate(text, from_code, to_code)
		if not cli_args.quiet:
			print(text + " => " + result)
	return result

def listen_and_translate(root, text_area):
	while True:
		data = stream.read(4096, exception_on_overflow=False)
		if recognizer.AcceptWaveform(data):
			result = json.loads(recognizer.Result())
			if "text" in result:
				if  result["text"]:
					translated = do_translate(result["text"])
				else:
					translated = ''
				update_text(text_area, translated)
		elif not cli_args.nopartial:
			partial = json.loads(recognizer.PartialResult())
			if "partial" in partial:
				if partial["partial"]:
					translated = do_translate(partial["partial"])
				else:
					translated = ''
				update_text(text_area, translated)
		root.update()



# Start the GUI and audio processing
(root, text_area) = create_ui()
print("****************** SPEAK ******************")
listen_and_translate(root, text_area)
root.mainloop()

