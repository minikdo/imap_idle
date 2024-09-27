#!/usr/bin/env python3

# Open a connection in IDLE mode and wait for notifications from the
# server.

import sys
import gpg
from imapclient import IMAPClient
import logging
import email.header

import time

from .settings import (
    HOST,
    PORT,
    USERNAME,
    ENCRYPTED_PASS,
    PASSWORDFILE,
)


logger = logging.getLogger(__name__)
logging.basicConfig(filename='/tmp/imap_idle_debug.log',
                    encoding='utf-8',
                    level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %I:%M:%S %p')


def get_password_from_file(passwordfile):
    with open(passwordfile) as f:
        return f.readlines()[0].rstrip()


def imap_login():
    password = get_password_from_file(PASSWORDFILE)
    print("instatiating IMAPClient...")
    server = IMAPClient(HOST, PORT)
    print(f"logging in {HOST}")
    server.login(USERNAME, password)
    print("selecting folder INBOX")
    server.select_folder("INBOX")
    return server

def main():

    server = imap_login()
    
    recent_messages = server.search(['RECENT'])
    
    messages = [
        m
        for m in recent_messages
    ]

    if len(recent_messages) == 0:
        print("no messages.")
        server.logout()
        print("logged out.")
        sys.exit(0)

    for msgid, data in server\
            .fetch(messages, ['ENVELOPE'])\
            .items():

        envelope = data[b'ENVELOPE']

        senders = [
            str(sender)
            for sender in envelope.sender
        ]

        subject = envelope.subject.decode()

        if subject.lower().startswith("=?utf-8?"):
            subject, _ = email.header.decode_header(subject)[0]
            subject = subject.decode()
                            
        print(f"ID #{msgid}, from: {senders}", end=" ")
        print(f"{subject}, received {envelope.date}")

    server.logout()
    print("logged out.")


if __name__ == '__main__':
    main()
