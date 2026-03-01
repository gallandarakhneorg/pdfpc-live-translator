#!/usr/bin/env bash

LAST_PAGE="1"

exec pdfpc -w none -P "$LAST_PAGE" "$@" "./TALK.pdf"
