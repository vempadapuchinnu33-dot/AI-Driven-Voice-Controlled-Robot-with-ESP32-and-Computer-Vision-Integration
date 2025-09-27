#!/usr/bin/env python3
"""
Command Parser Module for AI-Driven Voice Controlled Robot
Parses voice commands and converts them to robot actions
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List

class RobotAction(Enum):
    """Enumeration of possible robot actions"""
    MOVE_FORWARD = "move_forward"
    MOVE_BACKWARD = "move_backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    STOP = "stop"
    FIND_OBJECT = "find_object"
    FOLLOW_OBJECT = "follow_object"
    AVOID_OBSTACLE = "avoid_obstacle"
    UNKNOWN = "unknown"

@dataclass
class RobotCommand:
    """Data class for robot commands"""
    action: RobotAction
    parameters: Dict = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

class CommandParser:
    def __init__(self):
        """Initialize the command parser with predefined patterns"""
        self.command_patterns = {
            # Movement commands
            RobotAction.MOVE_FORWARD: [
                r'\b(move|go|walk|drive)\s+(forward|ahead|straight)\b',
                r'\b(forward|ahead)\b',
                r'\bmove\s+forward\b'
            ],
            RobotAction.MOVE_BACKWARD: [
                r'\b(move|go|walk|drive)\s+(backward|back|reverse)\b',
                r'\b(backward|back|reverse)\b',
                r'\bmove\s+back\b'
            ],
            RobotAction.TURN_LEFT: [
                r'\b(turn|rotate|spin)\s+(left|counterclockwise)\b',
                r'\b(left|turn\s+left)\b',
                r'\bgo\s+left\b'
            ],
            RobotAction.TURN_RIGHT: [
                r'\b(turn|rotate|spin)\s+(right|clockwise)\b',
                r'\b(right|turn\s+right)\b',
                r'\bgo\s+right\b'
            ],
            RobotAction.STOP: [
                r'\b(stop|halt|pause|brake)\b',
                r'\bstop\s+(moving|now)\b',
                r'\bfreeze\b'
            ],
            # Object interaction commands
            RobotAction.FIND_OBJECT: [
                r'\b(find|search|look\s+for|locate)\s+(\w+)\b',
                r'\bwhere\s+is\s+(\w+)\b',
                r'\bsearch\s+for\s+(\w+)\b'
            ],
            RobotAction.FOLLOW_OBJECT: [
                r'\b(follow|chase|track)\s+(\w+)\b',
                r'\bgo\s+to\s+(\w+)\b',
                r'\bmove\s+towards\s+(\w+)\b'
            ],
            RobotAction.AVOID_OBSTACLE: [
                r'\b(avoid|dodge|go\s+around)\s+(\w+)\b',
                r'\bstay\s+away\s+from\s+(\w+)\b'
            ]
        }
        
        # Common object names for object detection
        self.known_objects = [
            'ball', 'person', 'chair', 'table', 'bottle', 'cup', 'book',
            'phone', 'laptop', 'mouse', 'keyboard', 'car', 'bicycle',
            'dog', 'cat', 'bird', 'flower', 'tree', 'wall', 'door'
        ]
        
        logging.info("Command parser initialized")
    
    def parse_command(self, text: str) -> RobotCommand:
        """
        Parse a text command and return a RobotCommand object
        
        Args:
            text (str): The input text command
            
        Returns:
            RobotCommand: Parsed command with action and parameters
        """
        text = text.lower().strip()
        
        if not text:
            return RobotCommand(RobotAction.UNKNOWN, confidence=0.0)
        
        logging.info(f"Parsing command: '{text}'")
        
        # Try to match each action pattern
        for action, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    parameters = {}
                    confidence = 0.8
                    
                    # Extract object name for object-related commands
                    if action in [RobotAction.FIND_OBJECT, RobotAction.FOLLOW_OBJECT, RobotAction.AVOID_OBSTACLE]:
                        if match.groups():
                            # Get the last captured group that's not None
                            object_name = None
                            for group in reversed(match.groups()):
                                if group is not None:
                                    object_name = group
                                    break
                            
                            if object_name:
                                parameters['object'] = object_name
                                # Increase confidence if it's a known object
                                if object_name in self.known_objects:
                                    confidence = 0.9
                        else:
                            # Try to extract object name from the text
                            words = text.split()
                            for word in words:
                                if word in self.known_objects:
                                    parameters['object'] = word
                                    confidence = 0.7
                                    break
                    
                    # Extract speed/duration modifiers
                    speed_match = re.search(r'\b(slow|fast|quick|slowly|quickly)\b', text)
                    if speed_match:
                        parameters['speed'] = speed_match.group(1)
                    
                    duration_match = re.search(r'\b(\d+)\s*(second|minute|meter|step)s?\b', text)
                    if duration_match:
                        parameters['duration'] = int(duration_match.group(1))
                        parameters['unit'] = duration_match.group(2)
                    
                    command = RobotCommand(action, parameters, confidence)
                    logging.info(f"Parsed command: {command}")
                    return command
        
        # If no pattern matches, return unknown command
        logging.warning(f"Unknown command: '{text}'")
        return RobotCommand(RobotAction.UNKNOWN, {'original_text': text}, confidence=0.0)
    
    def get_action_description(self, command: RobotCommand) -> str:
        """
        Get a human-readable description of the command
        
        Args:
            command (RobotCommand): The command to describe
            
        Returns:
            str: Human-readable description
        """
        action = command.action
        params = command.parameters
        
        descriptions = {
            RobotAction.MOVE_FORWARD: "Move forward",
            RobotAction.MOVE_BACKWARD: "Move backward",
            RobotAction.TURN_LEFT: "Turn left",
            RobotAction.TURN_RIGHT: "Turn right",
            RobotAction.STOP: "Stop",
            RobotAction.FIND_OBJECT: f"Find {params.get('object', 'object')}",
            RobotAction.FOLLOW_OBJECT: f"Follow {params.get('object', 'object')}",
            RobotAction.AVOID_OBSTACLE: f"Avoid {params.get('object', 'obstacle')}",
            RobotAction.UNKNOWN: "Unknown command"
        }
        
        description = descriptions.get(action, "Unknown action")
        
        # Add modifiers
        if 'speed' in params:
            description += f" ({params['speed']})"
        if 'duration' in params:
            description += f" for {params['duration']} {params['unit']}s"
            
        return description

if __name__ == "__main__":
    # Test the command parser
    logging.basicConfig(level=logging.INFO)
    
    parser = CommandParser()
    
    test_commands = [
        "move forward",
        "turn left slowly",
        "find the ball",
        "follow the person",
        "stop now",
        "go backward for 5 seconds",
        "avoid the chair",
        "this is not a valid command"
    ]
    
    for cmd_text in test_commands:
        command = parser.parse_command(cmd_text)
        description = parser.get_action_description(command)
        print(f"'{cmd_text}' -> {description} (confidence: {command.confidence})")

