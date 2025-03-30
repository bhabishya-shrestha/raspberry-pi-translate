import asyncio
import base64
import json
import os
import tempfile
import wave

import RPi.GPIO as GPIO
import numpy as np
import requests
import sounddevice as sd
import websockets
from playsound import playsound

# Audio recording parameters
SAMPLE_RATE = 44100  # Sample rate in Hz

BUTTON_PIN = 27  # BCM pin number for the recording button
LED_PIN = 4      # GPIO pin for LED

# Flag controls LED pulse
processing_flag = False

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

led_pwm = GPIO.PWM(LED_PIN, 100)  # PWM on LED at 100 Hz
led_pwm.start(0)                  # LED starts off

###############################################################################
#                              GPIO Helpers
###############################################################################
def is_button_pressed():
    """Returns True if the button is pressed (pin is low)."""
    return GPIO.input(BUTTON_PIN) == 0

###############################################################################
#                            Network / API Calls
###############################################################################
def convert_wav_to_base64(wav_file_path):
    """Reads the WAV file and returns its Base64-encoded string."""
    with open(wav_file_path, 'rb') as wav_file:
        wav_data = wav_file.read()
    return base64.b64encode(wav_data).decode('utf-8')


def send_audio_to_api(wav_file_path, api_endpoint):
    """Sends the WAV file to the remote API endpoint as base64 data."""
    global processing_flag
    try:
        audio_blob = convert_wav_to_base64(wav_file_path)
        payload = {'audioBlob': audio_blob}
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(api_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            print("File uploaded successfully")
            print(response.json())
        else:
            print(f"Failed to upload file. Status code: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        processing_flag = False  # Stop processing after the API call completes


def download_and_play_audio(url, save_path='downloaded_audio.mp3'):
    """Downloads an audio file from `url`, saves it locally, then plays it."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, 'wb') as file:
                file.write(response.content)
            print(f"Audio file downloaded successfully: {save_path}")
            playsound(save_path)
            os.remove(save_path)  # Clean up the temporary file
        else:
            print(f"Failed to download audio file. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while downloading the audio file: {e}")

###############################################################################
#                            Recording Audio
###############################################################################
def record_audio():
    """Continuously records audio while button is pressed; saves it as WAV."""
    print("Recording... Press and hold the button to record")

    audio_data = []
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    stream.start()

    led_pwm.ChangeDutyCycle(100)  # Solid LED while recording
    try:
        while is_button_pressed():
            data, _ = stream.read(1024)
            audio_data.extend(data)
    finally:
        stream.stop()
        stream.close()
        print("Recording stopped")

    # Save recorded data as WAV
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        with wave.open(tmp_wav.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(np.array(audio_data, dtype='int16').tobytes())
        return tmp_wav.name

###############################################################################
#                               LED Pulsing
###############################################################################
async def pulse_led():
    """Continuously pulses the LED while `processing_flag` is True."""
    global processing_flag
    while processing_flag:
        for brightness in range(0, 101, 5):
            if not processing_flag:
                break
            led_pwm.ChangeDutyCycle(brightness)
            await asyncio.sleep(0.05)

        for brightness in range(100, -1, -5):
            if not processing_flag:
                break
            led_pwm.ChangeDutyCycle(brightness)
            await asyncio.sleep(0.05)

    # Ensure LED is off after processing
    led_pwm.ChangeDutyCycle(0)

###############################################################################
#                             WebSocket Handling
###############################################################################
async def connect_to_ws(uri, on_connect_event):
    """Connects to the WebSocket server and listens for messages."""
    global processing_flag
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to the WebSocket server")
            on_connect_event.set()  # Notify the main function of successful connection

            while True:
                response = await websocket.recv()
                print(f"WebSocket Response: {response}")

                try:
                    response_data = json.loads(response)
                    if response_data.get("action") == "TRANSLATE COMPLETE":
                        download_url = response_data.get("message")
                        download_and_play_audio(download_url)
                        processing_flag = False
                except json.JSONDecodeError:
                    print("Failed to parse JSON from WebSocket response")

    except Exception as e:
        print(f"An error occurred with WebSocket: {e}")

###############################################################################
#                                Main Logic
###############################################################################
async def run_main_logic():
    global processing_flag
    
    # Update to your actual endpoints
    ws_uri = 'wss://your_websocket_endpoint/'
    translate_endpoint = 'https://your_api_endpoint/'

    on_connect_event = asyncio.Event()
    ws_task = asyncio.create_task(connect_to_ws(ws_uri, on_connect_event))

    # Wait until the WebSocket is connected before proceeding
    await on_connect_event.wait()
    print("Press and hold the button to record...")

    try:
        while True:
            if is_button_pressed():
                # Record audio as WAV
                wav_path = record_audio()
                
                # After recording, set the flag to True for pulsing LED
                processing_flag = True
                pulse_task = asyncio.create_task(pulse_led())

                # Send audio to API
                send_audio_to_api(wav_path, translate_endpoint)

            await asyncio.sleep(0.1)  # Avoid tight loop
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        GPIO.cleanup()

# The following function is not an entry point, ensuring security
async def main():
    await run_main_logic()

if __name__ == '__main__':
    asyncio.run(main())
