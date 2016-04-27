#! python3
"""
Script to call and process the output of sync_torrent shell script

http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288

"""
import os
import sys
import subprocess
import time
from threading import Thread
import threading
import _thread
from queue import Queue, Empty
import re
import json
import logging
import yaml

pycharmMode = True  # Controls where the script will be run from

# -- Consts -- #
# Define constants from configuration
with open("config.yaml", 'r') as stream:
    config = yaml.load(stream)

    login = config['server']['username']
    passw = config['server']['password']
    host = config['server']['hostname']
    port = config['server']['port']
    # TODO: Enable support for multiple directories
    remote_dir = config['server']['remote_directories'][0]
    local_dir = config['server']['local_directories'][0]

# -- ------ -- #


def enqueue_output(out, queue, _event):
    for line in iter(out.readline, b''):
        # sys.stdout.flush()
        queue.put(line)
        if _event.isSet():
            out.close()
            _thread.exit()

    print("closing stdout")
    out.close()
    print("stdout closed")


def characterize_output(input):
    """
    (\[Connecting...\])
    c' [Connecting...]

    (\[Connected\])
No Regx, 13:cd `/home/jg1010/rtorrent/downloads/1Sync' [Connected]

    """
    results = re.search(r"`(.*)', got (\d*) of (\d*) \((\d*)%\)( \d*\.\d*(?:M|K)\/s)?(?: eta:(.*))?", input)
    if results is not None:
        return results 

    results = re.search(r"(\[Connected\])", input)
    if results is not None:
        return "connected"

    results = re.search(r"(\[Connecting...\])", input)
    if results is not None:
        return "connecting"

if __name__ == '__main__':

    subprocess.call(['rm', '/tmp/synctorrent.lock'])

    print("rm lock")
    time.sleep(0.1)
    logging.basicConfig(format="[%(asctime)s] %(name)s: %(message)s",
                        filename="pyLftp.log", level=logging.WARNING)
    logging.critical("pyLFTP STARTED!")
    event = threading.Event()
    while True:
        try:
            # os.system('clear')
            try: #C:/cygwin/bin/bash.exe
                ## process = subprocess.Popen(["C:/cygwin/bin/bash.exe", "./synct_py.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=0)
                process = subprocess.Popen(["./unbufferLFTP", port, login, passw, host, remote_dir, local_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)#, bufsize=0)
                ## process = subprocess.Popen(["/usr/bin/lftp", "-vvv", "-c open", ""], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=0)
                ## process = Popen(['script', '-q', '-c', 'lftp -c "open %s && pget %s"' % (host, path), '/dev/null'], stdin=open(os.devnull), stdout=PIPE, universal_newlines=True)


                print("lftp spawned")
            except BlockingIOError as e:
                print(e)
                time.sleep(1)
                continue
            q = Queue()
            event.clear()
            t = Thread(target=enqueue_output, args=(process.stdout, q, event))
            t.daemon = True # So the thread dies with the program
            t.start()

            count = 0
            while True:
                # output = process.stdout.readline()
                try:
                    output = q.get_nowait()
                except Empty:
                    output = None

                if output == None and process.poll() is not None:
                    break
                if output:
                    # print("{}:{}".format(count, output.strip()))
                    regex = characterize_output(output.strip())
                    if regex is not None:

                        if regex == "connecting":
                            print("Connecting to seedbox.")
                        elif regex == "connected":
                            print("Connected to seedbox.")
                        else:
                            regex_results = regex.groups()

                            name, bytes_retrived, total_bytes, precentage, speed, eta = regex_results
                            if speed is not None:
                                speed = "Speed: {},".format(speed.strip())
                            else:
                                speed = ""

                            if eta is not None:
                                eta = "ETA: {} left".format(eta)
                            else:
                                eta = ""
                            print("Currently retriving {}, with {} precent done. {} {}".format(name, precentage, speed, eta))
                            # logging.warning("Currently retriving {}, with {} precent done. {} {}".format(name, precentage, speed, eta))

                            js_data = {
                                'name': name,
                                'bytes_retrived': bytes_retrived,
                                'total_bytes': total_bytes,
                                'precentage': precentage,
                                'speed': speed,
                                'eta': eta
                            }

                    else:
                        print("{}".format(output.strip()))
                        logging.warning("{}".format(output.strip()))
                    count += 1
            return_code = process.poll()

            event.set()
            # threads = threading.enumerate()
            # print("# of threads: {}, {}".format(len(threads), threads) )

            delay_time = 10
            for second in range(60,-1,-delay_time):
                # os.system('clear')
                print("{}s remaining".format(second))
                time.sleep(delay_time)
        except KeyboardInterrupt as e:
            # TODO: Remove /tmp/synctorrent.lock

            event.set()
            input("press enter to exit")
            sys.exit(0)
