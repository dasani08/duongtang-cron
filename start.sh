#!/bin/sh

if test "$CRON_NAME"; then
    cp "crons/$CRON_NAME" /etc/crontabs/root
    chown root:root /etc/crontabs/root
    crond -f
fi
