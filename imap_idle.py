#!/usr/bin/env python3

# Open a connection in IDLE mode and wait for notifications from the
# server.

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
logging.basicConfig(filename='debug.log',
                    encoding='utf-8',
                    level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %I:%M:%S %p')


def get_password_with_gpg(encrypted_pass):
    with open(
            encrypted_pass,
            "rb") as cfile:
        try:
            plaintext, result, verify_result = gpg.Context().decrypt(cfile)
        except gpg.errors.GPGMEError as e:
            plaintext = None
            print(e)
        return plaintext.decode().rstrip()


def get_password_from_file(passwordfile):
    file = open(passwordfile)
    for line in file:
        if line.startswith("Pass"):
            return line.split(" ")[1].rstrip()
    return None


def imap_login():
    password = get_password_from_file(PASSWORDFILE)
    server = IMAPClient(HOST, PORT)
    server.login(USERNAME, password)
    server.select_folder("INBOX")
    server.idle()
    print("Connection is now in IDLE mode, quit with ^c")
    return server

def main():

    server = imap_login()
    
    login_time = time.time()
    
    previous_msgs = []
    
    while True:
        time_start = time.time()
        try:
            # Wait for up to 30 seconds for an IDLE response
            responses = server.idle_check(timeout=30)
    
            if responses and len(responses) > 1:
                if responses[1][1].decode() == 'RECENT':
    
                    server.idle_done()
    
                    recent_messages = server.search(['RECENT'])
    
                    messages = [
                        m
                        for m in recent_messages
                        if m not in previous_msgs
                    ]
                    
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
    
                    previous_msgs.extend(messages)
    
                    server.remove_flags(previous_msgs, [b'\\Seen'])
                    
                    server.idle()

            if responses:
                logger.debug('This message should go to the log file')
    
            time_end = time.time()
    
            if 'Still here' not in str(responses):
                if (time.time() - login_time) > 300:
                    logger.warning("Still here is missing more than 300s!")
                    logger.debug("restarting IDLE mode...")
                    server.idle_done()
                    server.idle()
            else:
                login_time = time.time()    
            
            logger.debug(f"while loop end {time_end - time_start}")
    
        except KeyboardInterrupt:
            break

    server.idle_done()
    print("\nIDLE mode done")
    server.logout()

if __name__ == '__main__':
    main()
