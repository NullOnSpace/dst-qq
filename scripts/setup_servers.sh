#!/usr/bin/env bash
HOME=/home/hikaru
LOG_DIR=

cd $LOG_DIR
find . -name 'server_log*.txt' -exec awk '/Client authenticated/ { printf "%s: %s" $4 $5 }' / | sort -u
