# LoraBrew

This repository contains all the code accompanying my blog post on [Brewing beer with LoRaWAN](https://reitsma.io/blog/lora-brew).

In the `client` directory you will find the code that runs on the embedded LoPy4 device.

In the `server` directory is a small FastAPI application that receives requests from the KPN Things Network, parses the payload and sends it to InfluxDB and Brewfather.

## Getting started

1. Clone this repo
1. In both the `client` and `server` directories, rename `secrets.sample.txt` to `secrets.txt` and fill in all the necessary fields.
1. Upload the `client` code to your LoPy4 device using your tool of choice. I used the Pymakr VSCode plugin.
1. Run the `server` code on a publicly accessible network. A `Dockerfile` is included.

You will have to connect the client and server yourself by configuring [KPN Things](https://docs.kpnthings.com/portal/concepts/devices/lora).
If you want to use [TTN](https://www.thethingsnetwork.org/) you might need to modify the payload parsing on the server side but the client code should be exactly the same.
