#!/usr/bin/env bash

PAGE=1

exec "`pwd`/start_talk_translate.py" --page "$PAGE" "$@" TALK.pdf
