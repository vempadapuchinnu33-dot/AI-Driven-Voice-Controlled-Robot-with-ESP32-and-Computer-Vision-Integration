#!/usr/bin/env python3
"""
Main Application for AI-Driven Voice Controlled Robot
Integrates voice recognition, command parsing, robot control, and computer vision
"""

import time
import logging
import threading
import signal
import sys
from typing import Optional

# Import custom modules
from voice_recognition import VoiceRecognizer
from command_parser import CommandParser, RobotAction
from robot_controller import RobotController
from computer_vision import ComputerVision

class VoiceControlledRobot:
    def __init__(self, robot_ip: str = "192.168.1.100", robot_port: int = 8080):
        """
        Initialize the voice-controlled robot system
        
        Args:
            robot_ip (str): IP address of the ESP32 robot
            robot_port (int): Port number for robot communication
        """
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.is_running = False
        
        # Initialize components
        self.voice_recognizer = None
        self.command_parser = CommandParser()
        self.robot_controller = RobotController(robot_ip, robot_port)
        self.computer_vision = ComputerVision(f"http://{robot_ip}:81/stream")
        
        # State variables
        self.current_mode = "voice_control"  # "voice_control" or "autonomous"
        self.last_command_time = 0
        self.command_timeout = 30  # seconds
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Voice-controlled robot system initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Shutdown signal received")
        self.stop()
        sys.exit(0)
    
    def start(self) -> bool:
        """
        Start the voice-controlled robot system
        
        Returns:
            bool: True if system started successfully, False otherwise
        """
        self.logger.info("Starting voice-controlled robot system...")
        
        try:
            # Initialize voice recognition
            self.voice_recognizer = VoiceRecognizer()
            
            # Connect to robot
            if not self.robot_controller.connect():
                self.logger.error("Failed to connect to robot")
                return False
            
            # Start computer vision
            if not self.computer_vision.start_camera():
                self.logger.error("Failed to start computer vision")
                return False
            
            # Start voice recognition
            self.voice_recognizer.start_listening()
            
            # Calibrate robot motors
            self.robot_controller.calibrate_motors()
            
            self.is_running = True
            
            # Start main control loop
            self.control_thread = threading.Thread(target=self._control_loop)
            self.control_thread.daemon = True
            self.control_thread.start()
            
            self.logger.info("Voice-controlled robot system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            return False
    
    def stop(self):
        """Stop the voice-controlled robot system"""
        self.logger.info("Stopping voice-controlled robot system...")
        
        self.is_running = False
        
        # Stop components
        if self.voice_recognizer:
            self.voice_recognizer.stop_listening()
        
        self.computer_vision.stop_camera()
        
        # Send emergency stop to robot
        self.robot_controller.emergency_stop()
        self.robot_controller.disconnect()
        
        # Wait for control thread to finish
        if hasattr(self, 'control_thread'):
            self.control_thread.join(timeout=2.0)
        
        self.logger.info("Voice-controlled robot system stopped")
    
    def _control_loop(self):
        """Main control loop"""
        self.logger.info("Starting main control loop")
        
        while self.is_running:
            try:
                if self.current_mode == "voice_control":
                    self._handle_voice_control()
                elif self.current_mode == "autonomous":
                    self._handle_autonomous_mode()
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                self.logger.error(f"Error in control loop: {e}")
                time.sleep(1.0)
    
    def _handle_voice_control(self):
        """Handle voice control mode"""
        # Get voice command
        command_text = self.voice_recognizer.get_command(timeout=0.1)
        
        if command_text:
            self.logger.info(f"Received voice command: '{command_text}'")
            
            # Parse command
            command = self.command_parser.parse_command(command_text)
            
            if command.confidence > 0.5:
                self._execute_command(command)
                self.last_command_time = time.time()
            else:
                self.logger.warning(f"Low confidence command ignored: {command_text}")
        
        # Check for command timeout (switch to autonomous mode)
        if time.time() - self.last_command_time > self.command_timeout:
            self.logger.info("No voice commands received, switching to autonomous mode")
            self.current_mode = "autonomous"
    
    def _handle_autonomous_mode(self):
        """Handle autonomous mode using computer vision"""
        # Look for interesting objects
        largest_object = self.computer_vision.get_largest_object()
        
        if largest_object:
            direction = self.computer_vision.get_object_direction(largest_object)
            
            self.logger.info(f"Autonomous mode: Found {largest_object.name} to the {direction}")
            
            # Simple autonomous behavior: move towards the largest object
            if direction == "left":
                self._move_robot("turn_left", duration=0.2)
            elif direction == "right":
                self._move_robot("turn_right", duration=0.2)
            elif direction == "center":
                if largest_object.area < 10000:  # Object is far away
                    self._move_robot("move_forward", duration=0.5)
                else:  # Object is close, stop
                    self._move_robot("stop")
        else:
            # No objects found, search by turning
            self._move_robot("turn_right", duration=0.3)
        
        # Check for voice commands to exit autonomous mode
        command_text = self.voice_recognizer.get_command(timeout=0.1)
        if command_text:
            self.logger.info("Voice command received, switching back to voice control mode")
            self.current_mode = "voice_control"
            self.last_command_time = time.time()
    
    def _execute_command(self, command):
        """Execute a parsed command"""
        description = self.command_parser.get_action_description(command)
        self.logger.info(f"Executing command: {description}")
        
        if command.action in [RobotAction.FIND_OBJECT, RobotAction.FOLLOW_OBJECT]:
            self._handle_vision_command(command)
        else:
            self.robot_controller.execute_command(command)
    
    def _handle_vision_command(self, command):
        """Handle commands that require computer vision"""
        object_name = command.parameters.get('object', '')
        
        if command.action == RobotAction.FIND_OBJECT:
            # Look for the specified object
            found_object = self.computer_vision.find_object(object_name)
            
            if found_object:
                direction = self.computer_vision.get_object_direction(found_object)
                self.logger.info(f"Found {object_name} to the {direction}")
                
                # Turn towards the object
                if direction == "left":
                    self._move_robot("turn_left", duration=0.5)
                elif direction == "right":
                    self._move_robot("turn_right", duration=0.5)
                else:
                    self.logger.info(f"{object_name} is in the center")
            else:
                self.logger.info(f"{object_name} not found, searching...")
                self._move_robot("turn_right", duration=1.0)
        
        elif command.action == RobotAction.FOLLOW_OBJECT:
            # Follow the specified object
            found_object = self.computer_vision.find_object(object_name)
            
            if found_object:
                direction = self.computer_vision.get_object_direction(found_object)
                
                if direction == "left":
                    self._move_robot("turn_left", duration=0.3)
                elif direction == "right":
                    self._move_robot("turn_right", duration=0.3)
                elif found_object.area < 8000:  # Object is far
                    self._move_robot("move_forward", duration=0.5)
                else:  # Object is close enough
                    self._move_robot("stop")
            else:
                self.logger.info(f"{object_name} lost, searching...")
                self._move_robot("turn_right", duration=0.5)
    
    def _move_robot(self, action: str, duration: float = 1.0):
        """Helper method to move the robot"""
        command_data = {
            'action': action,
            'duration': duration,
            'timestamp': time.time()
        }
        
        if action == "move_forward":
            command_data.update({'left_motor': 150, 'right_motor': 150})
        elif action == "move_backward":
            command_data.update({'left_motor': -150, 'right_motor': -150})
        elif action == "turn_left":
            command_data.update({'left_motor': -150, 'right_motor': 150})
        elif action == "turn_right":
            command_data.update({'left_motor': 150, 'right_motor': -150})
        elif action == "stop":
            command_data.update({'left_motor': 0, 'right_motor': 0})
        
        self.robot_controller.send_command(command_data)
    
    def get_system_status(self) -> dict:
        """Get the current system status"""
        return {
            'is_running': self.is_running,
            'current_mode': self.current_mode,
            'robot_connected': self.robot_controller.is_connected,
            'camera_active': self.computer_vision.is_running,
            'detected_objects': len(self.computer_vision.detected_objects),
            'last_command_time': self.last_command_time
        }

def main():
    """Main function"""
    # Configuration
    ROBOT_IP = "192.168.1.100"  # Change this to your robot's IP
    ROBOT_PORT = 8080
    
    # Create and start the robot system
    robot_system = VoiceControlledRobot(ROBOT_IP, ROBOT_PORT)
    
    if robot_system.start():
        try:
            print("Voice-controlled robot system is running...")
            print("Say commands like:")
            print("  - 'move forward'")
            print("  - 'turn left'")
            print("  - 'find the ball'")
            print("  - 'follow the person'")
            print("  - 'stop'")
            print("Press Ctrl+C to stop")
            
            # Keep the main thread alive
            while robot_system.is_running:
                status = robot_system.get_system_status()
                print(f"\rStatus: Mode={status['current_mode']}, "
                      f"Objects={status['detected_objects']}, "
                      f"Connected={status['robot_connected']}", end="")
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            robot_system.stop()
    else:
        print("Failed to start robot system")

if __name__ == "__main__":
    main()

