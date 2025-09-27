#!/usr/bin/env python3
"""
Robot Controller Module for AI-Driven Voice Controlled Robot
Handles communication with ESP32-based robot and motor control
"""

import socket
import json
import time
import threading
import logging
from typing import Dict, Optional, Tuple
from command_parser import RobotCommand, RobotAction

class RobotController:
    def __init__(self, robot_ip: str = "192.168.1.100", robot_port: int = 8080):
        """
        Initialize the robot controller
        
        Args:
            robot_ip (str): IP address of the ESP32 robot
            robot_port (int): Port number for communication
        """
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.socket = None
        self.is_connected = False
        self.command_lock = threading.Lock()
        
        # Movement parameters
        self.default_speed = 150  # PWM value (0-255)
        self.turn_duration = 0.5  # seconds
        self.move_duration = 1.0  # seconds
        
        logging.info(f"Robot controller initialized for {robot_ip}:{robot_port}")
    
    def connect(self) -> bool:
        """
        Establish connection to the robot
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5 second timeout
            self.socket.connect((self.robot_ip, self.robot_port))
            self.is_connected = True
            logging.info(f"Connected to robot at {self.robot_ip}:{self.robot_port}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to robot: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the robot"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_connected = False
        logging.info("Disconnected from robot")
    
    def send_command(self, command_data: Dict) -> bool:
        """
        Send a command to the robot
        
        Args:
            command_data (Dict): Command data to send
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.is_connected:
            logging.error("Not connected to robot")
            return False
        
        try:
            with self.command_lock:
                message = json.dumps(command_data) + '\n'
                self.socket.send(message.encode('utf-8'))
                logging.info(f"Sent command: {command_data}")
                return True
        except Exception as e:
            logging.error(f"Failed to send command: {e}")
            self.is_connected = False
            return False
    
    def execute_command(self, command: RobotCommand) -> bool:
        """
        Execute a parsed robot command
        
        Args:
            command (RobotCommand): The command to execute
            
        Returns:
            bool: True if command executed successfully, False otherwise
        """
        if command.action == RobotAction.UNKNOWN:
            logging.warning("Cannot execute unknown command")
            return False
        
        # Get speed from parameters or use default
        speed = self.default_speed
        if 'speed' in command.parameters:
            speed_modifier = command.parameters['speed']
            if speed_modifier in ['slow', 'slowly']:
                speed = int(self.default_speed * 0.6)
            elif speed_modifier in ['fast', 'quick', 'quickly']:
                speed = int(self.default_speed * 1.4)
        
        # Get duration from parameters or use default
        duration = None
        if 'duration' in command.parameters:
            duration = command.parameters['duration']
            if command.parameters.get('unit') == 'minute':
                duration *= 60
        
        # Create command data based on action
        command_data = {
            'action': command.action.value,
            'speed': speed,
            'timestamp': time.time()
        }
        
        if command.action == RobotAction.MOVE_FORWARD:
            command_data.update({
                'left_motor': speed,
                'right_motor': speed,
                'duration': duration or self.move_duration
            })
        
        elif command.action == RobotAction.MOVE_BACKWARD:
            command_data.update({
                'left_motor': -speed,
                'right_motor': -speed,
                'duration': duration or self.move_duration
            })
        
        elif command.action == RobotAction.TURN_LEFT:
            command_data.update({
                'left_motor': -speed,
                'right_motor': speed,
                'duration': duration or self.turn_duration
            })
        
        elif command.action == RobotAction.TURN_RIGHT:
            command_data.update({
                'left_motor': speed,
                'right_motor': -speed,
                'duration': duration or self.turn_duration
            })
        
        elif command.action == RobotAction.STOP:
            command_data.update({
                'left_motor': 0,
                'right_motor': 0,
                'duration': 0
            })
        
        elif command.action in [RobotAction.FIND_OBJECT, RobotAction.FOLLOW_OBJECT, RobotAction.AVOID_OBSTACLE]:
            command_data.update({
                'object': command.parameters.get('object', 'unknown'),
                'vision_mode': True
            })
        
        return self.send_command(command_data)
    
    def emergency_stop(self) -> bool:
        """
        Send emergency stop command to the robot
        
        Returns:
            bool: True if stop command sent successfully, False otherwise
        """
        stop_command = {
            'action': 'emergency_stop',
            'left_motor': 0,
            'right_motor': 0,
            'duration': 0,
            'timestamp': time.time()
        }
        return self.send_command(stop_command)
    
    def get_robot_status(self) -> Optional[Dict]:
        """
        Get the current status of the robot
        
        Returns:
            Dict: Robot status information or None if failed
        """
        if not self.is_connected:
            return None
        
        try:
            status_request = {
                'action': 'get_status',
                'timestamp': time.time()
            }
            self.send_command(status_request)
            
            # Wait for response (simplified - in real implementation, use proper protocol)
            self.socket.settimeout(2.0)
            response = self.socket.recv(1024).decode('utf-8')
            return json.loads(response)
        except Exception as e:
            logging.error(f"Failed to get robot status: {e}")
            return None
    
    def calibrate_motors(self) -> bool:
        """
        Calibrate the robot's motors
        
        Returns:
            bool: True if calibration successful, False otherwise
        """
        calibration_sequence = [
            {'action': 'calibrate', 'motor': 'left', 'speed': self.default_speed},
            {'action': 'calibrate', 'motor': 'right', 'speed': self.default_speed},
            {'action': 'calibrate', 'motor': 'both', 'speed': 0}
        ]
        
        for cmd in calibration_sequence:
            if not self.send_command(cmd):
                return False
            time.sleep(0.5)
        
        logging.info("Motor calibration completed")
        return True

if __name__ == "__main__":
    # Test the robot controller
    logging.basicConfig(level=logging.INFO)
    
    # Create a mock robot controller (won't actually connect)
    controller = RobotController("192.168.1.100", 8080)
    
    # Test command creation
    from command_parser import CommandParser
    
    parser = CommandParser()
    test_commands = [
        "move forward",
        "turn left",
        "stop",
        "find the ball"
    ]
    
    for cmd_text in test_commands:
        command = parser.parse_command(cmd_text)
        print(f"Command: {cmd_text}")
        print(f"Action: {command.action}")
        print(f"Parameters: {command.parameters}")
        print("---")

