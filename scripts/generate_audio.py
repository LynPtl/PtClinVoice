import wave
import struct
import math
import os

def generate_beep(filename, freq=440.0, duration=1.0, framerate=16000):
    obj = wave.open(filename, 'w')
    obj.setnchannels(1)
    obj.setsampwidth(2)
    obj.setframerate(framerate)
    length = int(duration * framerate)
    data = b''
    for i in range(length):
        val = int(32767.0 * math.cos(2 * math.pi * freq * i / framerate))
        data += struct.pack('<h', val)
    obj.writeframesraw(data)
    obj.close()
    
if __name__ == "__main__":
    os.makedirs('tests/fixtures', exist_ok=True)
    generate_beep('tests/fixtures/sample_english.wav', freq=440.0)
    generate_beep('tests/fixtures/sample_arabic.wav', freq=880.0)
    print("Test audio generated successfully.")
