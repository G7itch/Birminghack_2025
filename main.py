import numpy as np  # For signal processing
import sounddevice as sd  # For audio playback/recording
import wave  # For handling WAV files
import argparse  # For CLI arguments
import tkinter as tk  # For GUI (if needed)
from time import sleep
from scipy.signal import hilbert

# =========================
# Constants and Configuration
# =========================
BAUD_RATE = 45.45  # Standard RTTY baud rate
FREQ_MARK = 2125  # Frequency for 'mark' (1)
FREQ_SPACE = 2295  # Frequency for 'space' (0)
SAMPLE_RATE = 44100  # Audio sample rate in Hz
BIT_DURATION = 1 / BAUD_RATE  # Duration of each bit in seconds

sd.default.samplerate = SAMPLE_RATE 

# =========================
# File Parsing Function
# =========================
def parse_script_file(filename):
    """Extracts the content between the first and last two lines containing a single # each."""
    with open(filename, "r") as f:
        lines = f.readlines()
    
    # Find the first and last occurrence of two consecutive lines with a single #
    start_idx = None
    end_idx = None
    for i in range(len(lines) - 1):
        if lines[i].strip() == "#" and lines[i + 1].strip() == "#":
            if start_idx is None:
                start_idx = i + 2  # Start after these two lines
            else:
                end_idx = i
                break
    
    if start_idx is not None and end_idx is not None:
        return "".join(lines[start_idx:end_idx])
    else:
        raise ValueError("File does not contain properly formatted # markers.")

# =========================
# Encoding Functions
# =========================
def text_to_rtty(text):
    """Convert text into an RTTY signal representation."""
    bits = []
    for char in text:
        binary = format(ord(char), '07b')  # Convert to 7-bit binary
        bits.extend([0] + list(map(int, binary)) + [1])  # Start bit (0), data bits, stop bit (1)
    
    signal = np.array([])
    t = np.linspace(0, BIT_DURATION, int(SAMPLE_RATE * BIT_DURATION), endpoint=False)
    
    for bit in bits:
        freq = FREQ_MARK if bit == 1 else FREQ_SPACE
        wave = np.sin(2 * np.pi * freq * t)
        signal = np.concatenate((signal, wave))
    
    return signal

def generate_audio(signal):
    """Generate an audio waveform from RTTY signal data and play it."""
    sd.play(signal)
    sd.wait()

def write_to_cassette(data):
    """Play the encoded audio through the aux output."""
    generate_audio(data)

# =========================
# Decoding Functions
# =========================
def decode_audio(audio_data):
    """Convert recorded audio back into text data."""
    analytic_signal = hilbert(audio_data)
    amplitude_envelope = np.abs(analytic_signal)
    freq_data = np.fft.fft(audio_data)
    freq_bins = np.fft.fftfreq(len(audio_data), 1/SAMPLE_RATE)
    
    decoded_bits = []
    for i in range(0, len(freq_data), int(SAMPLE_RATE * BIT_DURATION)):
        segment = freq_data[i:i + int(SAMPLE_RATE * BIT_DURATION)]
        peak_freq = freq_bins[np.argmax(np.abs(segment))]
        decoded_bits.append(1 if abs(peak_freq - FREQ_MARK) < abs(peak_freq - FREQ_SPACE) else 0)
    
    chars = []
    for i in range(0, len(decoded_bits), 9):
        if i + 9 <= len(decoded_bits):
            char_bits = decoded_bits[i+1:i+8]  # Ignore start bit (0) and stop bit (1)
            char = chr(int("".join(map(str, char_bits)), 2))
            chars.append(char)
    
    return "".join(chars)

# =========================
# Reading Functions
# =========================
def read_from_cassette():
    """Record input audio and decode it."""
    print("Recording...")
    audio_data = sd.rec(int(10 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    print("Processing recorded audio...")
    decoded_text = decode_audio(audio_data.flatten())
    print("Decoded text:", decoded_text)
    return decoded_text

# =========================
# CLI Interface
# =========================
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="RTTY Cassette Writer")
    parser.add_argument("--write", type=str, help="Text to write to cassette")
    parser.add_argument("--read", action="store_true", help="Read from cassette")
    parser.add_argument("--file", type=str, help="Path to a Python script to extract text from")
    return parser.parse_args()

# =========================
# GUI Interface (Optional)
# =========================
def launch_gui():
    """Launch a simple GUI for the project."""
    pass  # TODO: Implement GUI if needed

# =========================
# Main Execution
# =========================
if __name__ == "__main__":
    args = parse_args()
    
    if args.file:
        try:
            extracted_text = parse_script_file(args.file)
            print(f"Extracted text:\n{extracted_text}")
            args.write = extracted_text.strip()  # Automatically write extracted text
        except ValueError as e:
            print(f"Error: {e}")
    
    if args.write:
        print(f"Writing: {args.write}")
        sleep(8)  # Guarantees that the non-writable beginning of tape won't be used in program
        data = text_to_rtty(args.write)
        write_to_cassette(data)
    
    if args.read:
        print("Reading from cassette...")
        read_from_cassette()
