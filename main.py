import os
import sys

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir)
sys.path.append(mymodule_dir)

from sipfullproxy import UDPHandler
from socketserver import UDPServer
import socket
from threading import Thread
import time
import logging


def main():
    ip = "0.0.0.0"
    port = 5060

    logging.basicConfig(filename="sip.log", encoding="utf-8", level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%H:%M:%S')
    logging.info("STARTED - " + time.strftime("%a, %d %b %Y %H:%M:%S ", time.localtime()))
    hostname = socket.gethostname()
    #ip = socket.gethostbyname(hostname)
    print(f"IP: {ip}")
    logging.info(hostname)
    logging.info(f"{ip}:{port}")

    with UDPServer((ip, port), UDPHandler) as proxy:
        proxy.recordroute = f"Record-Route: <sip:{ip}:{port};lr>"
        proxy.topvia = f"Via: SIP/2.0/UDP {ip}:{port}"
        proxy.logging = logging

        server_thread = Thread(None, proxy.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        while input("Type '.q' to exit: ") != ".q":
            continue

        proxy.shutdown()
        proxy.server_close()
        server_thread.join()

    logging.info("ENDED - " + time.strftime("%a, %d %b %Y %H:%M:%S ", time.localtime()))
    sys.exit(0)


if __name__ == "__main__":
    main()
