# Live Translator for PDFPC

This repository provides a window overlay that is showing live translation on the top of [PDFPC viewer](https://pdfpc.github.io/).

The tool does:

1. start [PDFPC viewer](https://pdfpc.github.io/)
2. capture of the sound wave from the default microphone (using VOSK)
3. translate the captured text (from English to Chinese by default)
4. show the translation result on a overlay window

# Requirements

* [PDFPC viewer](https://pdfpc.github.io/) must be installed on your system

# Installation of the translation script

The following elements must be installed to have the live translation working.

## System-wide installation

You must install Python and its virtual environment.

```bash
sudo apt install python3-full
sudo apt install python3-venv
```


## Create Python virtual env

Create the Python virtual environment to install the live translation libraries.

```bash
mkdir ~/bin/python3_environments
cd ~/bin/python3_environments
python3 -m venv live_translator
```


## Install local libraries

Install the libraries in the virtual environment

```bash
~/bin/python3_environments/live_translator/bin/pip install tk
~/bin/python3_environments/live_translator/bin/pip install pydub
~/bin/python3_environments/live_translator/bin/pip install screeninfo
~/bin/python3_environments/live_translator/bin/pip install whisper
~/bin/python3_environments/live_translator/bin/pip install faster-whisper
```


## Install VOSK

VOSK is used for capturing the sound wave from the microphone ad converting offline it to text.

```bash
~/bin/python3_environments/live_translator/bin/pip install vosk
```

* Download the English model from [VOSK models](https://alphacephei.com/vosk/models) and extract it.
* Update the launching script with the full path to the downloaded library.


## Install PyAudio

PyAudio is used for reading the microphone.

```bash
sudo apt install portaudio19-dev
~/bin/python3_environments/live_translator/bin/pip install pyaudio
```


## Install ARGOS

ARGOS is used for translating offline the text from a source language to a target language.

```bash
~/bin/python3_environments/live_translator/bin/pip install argostranslate
```


## Install the English-Chinese package:

Below, you could specify the translation dictionary to be installed.

```bash
~/bin/python3_environments/live_translator/bin/argospm install translate-en_zh
```

# Author

* Stéphane GALLAND <http://www.ciad-lab.fr/stephane_galland/>

# License

This tool is distributed under the [Apache v2 license](./LICENSE), and is copyrigthed to the original authors and the other authors.

