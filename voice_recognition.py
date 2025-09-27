#!/usr/bin/env python3
"""
Voice Recognition Module for AI-Driven Voice Controlled Robot
Uses VOSK for offline speech recognition
"""

import json
import pyaudio
import vosk
import threading
import queue
import logging

class VoiceRecognizer:
    def __init__(self, model_path="vosk-model-en-us-0.22", sample_rate=16000):
        """
        Initialize the voice recognizer
        
        Args:
            model_path (str): Path to the VOSK model
            sample_rate (int): Audio sample rate
        """
        self.sample_rate = sample_rate
        self.chunk_size = 4096
        self.command_queue = queue.Queue()
        self.is_listening = False
        
        # Initialize VOSK model
        try:
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
            logging.info("VOSK model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load VOSK model: {e}")
            raise
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
    def start_listening(self):
        """Start the voice recognition thread"""
        if not self.is_listening:
            self.is_listening = True
            self.listen_thread = threading.Thread(target=self._listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            logging.info("Voice recognition started")
    
    def stop_listening(self):
        """Stop the voice recognition"""
        self.is_listening = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join()
        logging.info("Voice recognition stopped")
    
    def _listen_loop(self):
        """Main listening loop"""
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logging.info("Listening for voice commands...")
            
            while self.is_listening:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        self.command_queue.put(text)
                        logging.info(f"Recognized command: {text}")
                        
        except Exception as e:
            logging.error(f"Error in voice recognition: {e}")
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
    
    def get_command(self, timeout=None):
        """
        Get the next recognized command
        
        Args:
            timeout (float): Timeout in seconds
            
        Returns:
            str: Recognized command text or None if timeout
        """
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'audio'):
            self.audio.terminate()

if __name__ == "__main__":
    # Test the voice recognizer
    logging.basicConfig(level=logging.INFO)
    
    recognizer = VoiceRecognizer()
    recognizer.start_listening()
    
    try:
        while True:
            command = recognizer.get_command(timeout=1.0)
            if command:
                print(f"Command received: {command}")
    except KeyboardInterrupt:
        print("Stopping voice recognition...")
        recognizer.stop_listening()

