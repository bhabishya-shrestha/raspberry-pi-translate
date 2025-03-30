# Raspberry Pi Audio Recording and Playback System

## Project Overview

This project enables audio recording and playback using a Raspberry Pi. It captures audio when a button is pressed, sends the audio to a remote API for processing, and can download and play audio files from a specified URL.

## Features

- Record audio in WAV format while holding a button.
- Encode recorded audio to Base64 for API transmission.
- Download and play audio files from a given URL.
- Visual feedback via an LED during recording and processing.
- Real-time communication with a WebSocket server.

## Requirements

- Raspberry Pi with Raspbian OS
- Python 3.x
- Required Python libraries:
  - `numpy`
  - `requests`
  - `sounddevice`
  - `playsound`
  - `websockets`
  - `RPi.GPIO`

## GPIO Pin Configuration
  - Button Pin: 27 (BCM)
  - LED Pin: 4 (BCM)
Install the required libraries using pip:

```bash
pip install numpy requests sounddevice playsound websockets RPi.GPIO

