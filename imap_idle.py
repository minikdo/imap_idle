#!/usr/bin/env python3

import sys
import json
from pathlib import Path
from types import SimpleNamespace
from email.header import decode_header, make_header

from imapclient import IMAPClient


class Imap:
    """ Connects to IMAP server and sets IDLE mode
    to wait for new messages. """

    secrets = (Path(__file__).parent / "secrets.json").resolve()
    with open(secrets, encoding="utf-8") as f:
        secrets = json.loads(f.read())
        config = SimpleNamespace(**secrets)

    def __init__(self) -> None:
        print(f"Connecting to {self.config.HOST}")
        self.server = self.login()

    def get_password(self, passwordfile) -> str:
        """ Gets imap password from a local file. """
        with open(passwordfile, encoding="utf-8") as f:
            password = f.readlines()[0].rstrip()
        return password

    def login(self):
        """ Logs in and start IDLE mode. """
        password = self.get_password(self.config.PASSWORDFILE)
        server = IMAPClient(self.config.HOST, self.config.PORT)
        server.login(self.config.USERNAME, password)
        server.select_folder("INBOX")
        return server

    def start_idle(self) -> None:
        self.server.idle()
        print("Connection is now in IDLE mode, quit with ^c")

    def check_new(self) -> bool:
        """ Checks if there are messages with flag RECENT. """
        try:
            resp = self.server.idle_check(timeout=30)
        except KeyboardInterrupt:
            sys.exit(0)
        if len(resp) > 1 and resp[1][1].decode() == 'RECENT':
            return True
        return False

    def get_recent_ids(self):
        return self.server.search(['RECENT'])

    def fetch_messages(self, recent_ids):
        return self.server.fetch(recent_ids, ['ENVELOPE'])

    def decode_utf8(self, data) -> str:
        decoded = make_header(decode_header(data))
        return str(decoded)

    def process_envelope(self, msg) -> tuple[str, ...]:
        msgid, data = msg
        envelope = data[b'ENVELOPE']
        return (
            msgid,
            self.decode_utf8(str(envelope.sender[0])),
            self.decode_utf8(envelope.subject.decode()),
            envelope.date,
        )

    def print_msgs(self, msgs_ids) -> None:
        msgs = self.fetch_messages(msgs_ids)
        for msg in msgs.items():
            msgid, sender, subject, date = self.process_envelope(msg)

            print(f"ID #{msgid}, from: {sender}",
                  f"{subject}, received {date}")


def main():

    imap = Imap()

    argv = sys.argv
    if len(argv) > 1 and argv[1] == '-l':
        # Only fetch recent emails and exit
        msgs_ids = imap.get_recent_ids()
        imap.print_msgs(msgs_ids)
        sys.exit(0)

    imap.start_idle()

    previous_msgs = []

    while True:

        if not imap.check_new():
            continue

        # Stop IDLE mode
        imap.server.idle_done()

        msgs_ids = [
            m
            for m in imap.get_recent_ids()
            if m not in previous_msgs
        ]

        imap.print_msgs(msgs_ids)

        previous_msgs.extend(msgs_ids)
        imap.server.remove_flags(previous_msgs, [b'\\Seen'])

        # Resume IDLE mode
        imap.server.idle()


if __name__ == '__main__':
    main()
