import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from gi.repository import GLib
from ctypes import *
import time
import math
import platform
import json
import pyds
import socket
import ctypes
import sys
import _thread
from flask import Flask, request

app = Flask(__name__)

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True


def gen_rtp(filename, address, port, interface):
    pipe_str = f"filesrc name=filesrc location={filename} ! "
    if filename.endswith(".pcap"):
        pipe_str += "pcapparse ! "
    else:
        if filename.endswith(".mp4"):
            pipe_str += "qtdemux ! "
        elif filename.endswith(".mkv"):
            pipe_str += "matroskademux ! "
        pipe_str += "h264parse ! mpegtsmux ! rtpmp2tpay ! "
    pipe_str += f"udpsink host={address} port={port}"
    if interface:
        pipe_str += f" multicast-iface={interface}"
    pipe_str += f" sync=true"

    pipeline = Gst.parse_launch(pipe_str)
    if not pipeline:
        print("failed to start pipeline")
    pipeline.set_state(Gst.State.PLAYING)
    print(f"playing pipeline:\n ~~~ {pipe_str}")
    return pipeline


def run_pipe(filename, address, port, interface):
    pipeline = gen_rtp(filename, address, port, interface)
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)
    try:
        loop.run()
    except:
        pass
    print("\nExiting app")
    pipeline.set_state(Gst.State.NULL)


@app.route('/', methods=['POST'])
def main():
    body = request.get_json()
    _thread.start_new_thread(run_pipe, (body["file"], body["address"], body["port"], body["nic"]))
    return {"status": True}


if __name__ == '__main__':
    GObject.threads_init()
    Gst.init(None)
    app.run(port=1234)
