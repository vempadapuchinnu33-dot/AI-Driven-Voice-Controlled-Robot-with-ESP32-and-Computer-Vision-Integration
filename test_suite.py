#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI-Driven Voice Controlled Robot
Tests all components and their integration
"""

import unittest
import time
import threading
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
from command_parser import CommandParser, RobotAction, RobotCommand
from robot_controller import RobotController
from computer_vision import ComputerVision, DetectedObject

class TestCommandParser(unittest.TestCase):
    """Test cases for the command parser module"""
    
    def setUp(self):
        self.parser = CommandParser()
    
    def test_movement_commands(self):
        """Test basic movement command parsing"""
        test_cases = [
            ("move forward", RobotAction.MOVE_FORWARD),
            ("go ahead", RobotAction.MOVE_FORWARD),
            ("move backward", RobotAction.MOVE_BACKWARD),
            ("go back", RobotAction.MOVE_BACKWARD),
            ("turn left", RobotAction.TURN_LEFT),
            ("turn right", RobotAction.TURN_RIGHT),
            ("stop", RobotAction.STOP),
            ("halt", RobotAction.STOP)
        ]
        
        for command_text, expected_action in test_cases:
            with self.subTest(command=command_text):
                result = self.parser.parse_command(command_text)
                self.assertEqual(result.action, expected_action)
                self.assertGreater(result.confidence, 0.5)
    
    def test_object_commands(self):
        """Test object-related command parsing"""
        test_cases = [
            ("find the ball", RobotAction.FIND_OBJECT, "ball"),
            ("search for person", RobotAction.FIND_OBJECT, "person"),
            ("follow the cat", RobotAction.FOLLOW_OBJECT, "cat"),
            ("avoid the chair", RobotAction.AVOID_OBSTACLE, "chair")
        ]
        
        for command_text, expected_action, expected_object in test_cases:
            with self.subTest(command=command_text):
                result = self.parser.parse_command(command_text)
                self.assertEqual(result.action, expected_action)
                self.assertEqual(result.parameters.get('object'), expected_object)
                self.assertGreater(result.confidence, 0.5)
    
    def test_speed_modifiers(self):
        """Test speed modifier parsing"""
        result = self.parser.parse_command("move forward slowly")
        self.assertEqual(result.action, RobotAction.MOVE_FORWARD)
        self.assertEqual(result.parameters.get('speed'), 'slowly')
        
        result = self.parser.parse_command("turn left quickly")
        self.assertEqual(result.action, RobotAction.TURN_LEFT)
        self.assertEqual(result.parameters.get('speed'), 'quickly')
    
    def test_duration_modifiers(self):
        """Test duration modifier parsing"""
        result = self.parser.parse_command("move forward for 5 seconds")
        self.assertEqual(result.action, RobotAction.MOVE_FORWARD)
        self.assertEqual(result.parameters.get('duration'), 5)
        self.assertEqual(result.parameters.get('unit'), 'second')
    
    def test_unknown_commands(self):
        """Test handling of unknown commands"""
        unknown_commands = [
            "this is not a command",
            "random text",
            "",
            "xyz abc def"
        ]
        
        for command_text in unknown_commands:
            with self.subTest(command=command_text):
                result = self.parser.parse_command(command_text)
                self.assertEqual(result.action, RobotAction.UNKNOWN)
                self.assertEqual(result.confidence, 0.0)
    
    def test_command_description(self):
        """Test command description generation"""
        command = RobotCommand(RobotAction.MOVE_FORWARD, {'speed': 'fast'})
        description = self.parser.get_action_description(command)
        self.assertIn("Move forward", description)
        self.assertIn("fast", description)

class TestRobotController(unittest.TestCase):
    """Test cases for the robot controller module"""
    
    def setUp(self):
        self.controller = RobotController("127.0.0.1", 8080)
    
    @patch('socket.socket')
    def test_connection(self, mock_socket):
        """Test robot connection"""
        mock_socket_instance = Mock()
        mock_socket.return_value = mock_socket_instance
        
        # Test successful connection
        result = self.controller.connect()
        self.assertTrue(result)
        self.assertTrue(self.controller.is_connected)
        
        # Test connection failure
        mock_socket_instance.connect.side_effect = Exception("Connection failed")
        result = self.controller.connect()
        self.assertFalse(result)
        self.assertFalse(self.controller.is_connected)
    
    def test_command_data_generation(self):
        """Test command data generation for different actions"""
        parser = CommandParser()
        
        # Test forward movement
        command = parser.parse_command("move forward")
        self.controller.is_connected = True
        
        with patch.object(self.controller, 'send_command') as mock_send:
            self.controller.execute_command(command)
            mock_send.assert_called_once()
            
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['action'], 'move_forward')
            self.assertGreater(call_args['left_motor'], 0)
            self.assertGreater(call_args['right_motor'], 0)
    
    def test_emergency_stop(self):
        """Test emergency stop functionality"""
        self.controller.is_connected = True
        
        with patch.object(self.controller, 'send_command') as mock_send:
            result = self.controller.emergency_stop()
            self.assertTrue(result)
            
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['action'], 'emergency_stop')
            self.assertEqual(call_args['left_motor'], 0)
            self.assertEqual(call_args['right_motor'], 0)

class TestComputerVision(unittest.TestCase):
    """Test cases for the computer vision module"""
    
    def setUp(self):
        self.cv_module = ComputerVision()
    
    def test_object_detection_data_structure(self):
        """Test detected object data structure"""
        obj = DetectedObject(
            name="test_ball",
            confidence=0.8,
            bbox=(10, 20, 50, 60),
            center=(35, 50),
            area=3000
        )
        
        self.assertEqual(obj.name, "test_ball")
        self.assertEqual(obj.confidence, 0.8)
        self.assertEqual(obj.bbox, (10, 20, 50, 60))
        self.assertEqual(obj.center, (35, 50))
        self.assertEqual(obj.area, 3000)
    
    def test_object_direction_calculation(self):
        """Test object direction calculation"""
        # Object on the left
        obj_left = DetectedObject("ball", 0.8, (50, 50, 30, 30), (65, 65), 900)
        direction = self.cv_module.get_object_direction(obj_left, frame_width=640)
        self.assertEqual(direction, "left")
        
        # Object in the center
        obj_center = DetectedObject("ball", 0.8, (310, 50, 30, 30), (325, 65), 900)
        direction = self.cv_module.get_object_direction(obj_center, frame_width=640)
        self.assertEqual(direction, "center")
        
        # Object on the right
        obj_right = DetectedObject("ball", 0.8, (550, 50, 30, 30), (565, 65), 900)
        direction = self.cv_module.get_object_direction(obj_right, frame_width=640)
        self.assertEqual(direction, "right")
    
    def test_find_object(self):
        """Test object finding functionality"""
        # Mock detected objects
        self.cv_module.detected_objects = [
            DetectedObject("red_ball", 0.8, (10, 10, 30, 30), (25, 25), 900),
            DetectedObject("blue_ball", 0.7, (50, 50, 25, 25), (62, 62), 625),
            DetectedObject("person", 0.9, (100, 100, 60, 80), (130, 140), 4800)
        ]
        
        # Test finding existing object
        found_ball = self.cv_module.find_object("ball")
        self.assertIsNotNone(found_ball)
        self.assertIn("ball", found_ball.name)
        
        # Test finding non-existing object
        found_car = self.cv_module.find_object("car")
        self.assertIsNone(found_car)
    
    def test_largest_object_detection(self):
        """Test largest object detection"""
        # Mock detected objects with different sizes
        self.cv_module.detected_objects = [
            DetectedObject("small_ball", 0.8, (10, 10, 20, 20), (20, 20), 400),
            DetectedObject("large_ball", 0.7, (50, 50, 40, 40), (70, 70), 1600),
            DetectedObject("medium_ball", 0.9, (100, 100, 30, 30), (115, 115), 900)
        ]
        
        largest = self.cv_module.get_largest_object()
        self.assertIsNotNone(largest)
        self.assertEqual(largest.name, "large_ball")
        self.assertEqual(largest.area, 1600)

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.parser = CommandParser()
        self.controller = RobotController("127.0.0.1", 8080)
        self.cv_module = ComputerVision()
    
    def test_voice_to_robot_pipeline(self):
        """Test the complete pipeline from voice command to robot action"""
        # Simulate voice command
        voice_text = "move forward slowly"
        
        # Parse command
        command = self.parser.parse_command(voice_text)
        self.assertEqual(command.action, RobotAction.MOVE_FORWARD)
        self.assertEqual(command.parameters.get('speed'), 'slowly')
        
        # Mock robot controller
        self.controller.is_connected = True
        with patch.object(self.controller, 'send_command') as mock_send:
            result = self.controller.execute_command(command)
            self.assertTrue(result)
            
            # Verify command data
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['action'], 'move_forward')
            # Speed should be reduced for 'slowly' modifier
            self.assertLess(call_args['speed'], self.controller.default_speed)
    
    def test_vision_guided_movement(self):
        """Test vision-guided robot movement"""
        # Mock detected object
        self.cv_module.detected_objects = [
            DetectedObject("ball", 0.8, (100, 100, 30, 30), (115, 115), 900)
        ]
        
        # Parse find command
        command = self.parser.parse_command("find the ball")
        self.assertEqual(command.action, RobotAction.FIND_OBJECT)
        self.assertEqual(command.parameters.get('object'), 'ball')
        
        # Find object
        found_object = self.cv_module.find_object("ball")
        self.assertIsNotNone(found_object)
        
        # Get direction
        direction = self.cv_module.get_object_direction(found_object)
        self.assertEqual(direction, "left")  # Object at x=115 should be left of center

class TestPerformanceMetrics(unittest.TestCase):
    """Performance and reliability tests"""
    
    def test_command_parsing_speed(self):
        """Test command parsing performance"""
        parser = CommandParser()
        commands = [
            "move forward", "turn left", "stop", "find the ball",
            "follow the person", "move backward slowly", "turn right quickly"
        ]
        
        start_time = time.time()
        for _ in range(1000):
            for cmd in commands:
                parser.parse_command(cmd)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_command = total_time / (1000 * len(commands))
        
        # Command parsing should be fast (< 1ms per command)
        self.assertLess(avg_time_per_command, 0.001)
        print(f"Average command parsing time: {avg_time_per_command*1000:.3f}ms")
    
    def test_memory_usage(self):
        """Test memory usage of components"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create multiple instances
        parsers = [CommandParser() for _ in range(10)]
        controllers = [RobotController("127.0.0.1", 8080) for _ in range(10)]
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for 20 instances)
        self.assertLess(memory_increase, 50 * 1024 * 1024)
        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f}MB")

def run_performance_tests():
    """Run performance benchmarks and generate metrics"""
    print("Running Performance Tests...")
    print("=" * 50)
    
    # Test command parsing accuracy
    parser = CommandParser()
    test_commands = [
        ("move forward", RobotAction.MOVE_FORWARD),
        ("turn left slowly", RobotAction.TURN_LEFT),
        ("find the red ball", RobotAction.FIND_OBJECT),
        ("stop now", RobotAction.STOP),
        ("follow the person", RobotAction.FOLLOW_OBJECT),
        ("avoid the chair", RobotAction.AVOID_OBSTACLE),
        ("go backward for 3 seconds", RobotAction.MOVE_BACKWARD),
        ("turn right quickly", RobotAction.TURN_RIGHT)
    ]
    
    correct_predictions = 0
    total_predictions = len(test_commands)
    
    for command_text, expected_action in test_commands:
        result = parser.parse_command(command_text)
        if result.action == expected_action:
            correct_predictions += 1
        print(f"'{command_text}' -> {result.action.value} (confidence: {result.confidence:.2f})")
    
    accuracy = correct_predictions / total_predictions
    print(f"\nCommand Parsing Accuracy: {accuracy:.2%}")
    
    # Test response time
    start_time = time.time()
    for _ in range(100):
        parser.parse_command("move forward")
    end_time = time.time()
    
    avg_response_time = (end_time - start_time) / 100
    print(f"Average Response Time: {avg_response_time*1000:.2f}ms")
    
    return {
        'accuracy': accuracy,
        'response_time': avg_response_time,
        'total_tests': total_predictions,
        'correct_predictions': correct_predictions
    }

if __name__ == "__main__":
    # Run unit tests
    print("Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*50)
    
    # Run performance tests
    metrics = run_performance_tests()
    
    print("\n" + "="*50)
    print("Test Summary:")
    print(f"Command Parsing Accuracy: {metrics['accuracy']:.2%}")
    print(f"Average Response Time: {metrics['response_time']*1000:.2f}ms")
    print(f"Tests Passed: {metrics['correct_predictions']}/{metrics['total_tests']}")

