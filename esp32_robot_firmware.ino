/*
 * ESP32 Robot Firmware for AI-Driven Voice Controlled Robot
 * Handles Wi-Fi communication, motor control, and camera streaming
 */

#include <WiFi.h>
#include <WiFiServer.h>
#include <ArduinoJson.h>
#include <esp_camera.h>

// Wi-Fi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server configuration
WiFiServer server(8080);
WiFiServer cameraServer(81);

// Motor pins (L298N motor driver)
const int motor1Pin1 = 2;
const int motor1Pin2 = 4;
const int motor1Enable = 5;
const int motor2Pin1 = 16;
const int motor2Pin2 = 17;
const int motor2Enable = 18;

// LED pin for status indication
const int statusLED = 33;

// Camera configuration for ESP32-CAM
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Global variables
bool motorsEnabled = true;
unsigned long lastCommandTime = 0;
const unsigned long commandTimeout = 5000; // 5 seconds

void setup() {
  Serial.begin(115200);
  
  // Initialize pins
  pinMode(motor1Pin1, OUTPUT);
  pinMode(motor1Pin2, OUTPUT);
  pinMode(motor1Enable, OUTPUT);
  pinMode(motor2Pin1, OUTPUT);
  pinMode(motor2Pin2, OUTPUT);
  pinMode(motor2Enable, OUTPUT);
  pinMode(statusLED, OUTPUT);
  
  // Initialize motors (stopped)
  stopMotors();
  
  // Initialize camera
  initCamera();
  
  // Connect to Wi-Fi
  connectToWiFi();
  
  // Start servers
  server.begin();
  cameraServer.begin();
  
  Serial.println("ESP32 Robot ready!");
  digitalWrite(statusLED, HIGH);
}

void loop() {
  // Handle command server
  handleCommandServer();
  
  // Handle camera server
  handleCameraServer();
  
  // Safety timeout - stop motors if no command received
  if (millis() - lastCommandTime > commandTimeout && motorsEnabled) {
    stopMotors();
    Serial.println("Command timeout - motors stopped");
  }
  
  delay(10);
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(statusLED, !digitalRead(statusLED)); // Blink LED
  }
  
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  digitalWrite(statusLED, HIGH);
}

void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  Serial.println("Camera initialized");
}

void handleCommandServer() {
  WiFiClient client = server.available();
  
  if (client) {
    Serial.println("New client connected");
    
    while (client.connected()) {
      if (client.available()) {
        String jsonString = client.readStringUntil('\n');
        jsonString.trim();
        
        if (jsonString.length() > 0) {
          processCommand(jsonString);
          lastCommandTime = millis();
        }
      }
    }
    
    client.stop();
    Serial.println("Client disconnected");
  }
}

void handleCameraServer() {
  WiFiClient client = cameraServer.available();
  
  if (client) {
    String request = client.readStringUntil('\r');
    client.flush();
    
    if (request.indexOf("/stream") != -1) {
      streamCamera(client);
    }
    
    client.stop();
  }
}

void streamCamera(WiFiClient &client) {
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
  client.println();
  
  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      break;
    }
    
    client.println("--frame");
    client.println("Content-Type: image/jpeg");
    client.print("Content-Length: ");
    client.println(fb->len);
    client.println();
    
    client.write(fb->buf, fb->len);
    client.println();
    
    esp_camera_fb_return(fb);
    
    delay(30); // ~30 FPS
  }
}

void processCommand(String jsonString) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, jsonString);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  String action = doc["action"];
  Serial.print("Received command: ");
  Serial.println(action);
  
  if (action == "emergency_stop") {
    stopMotors();
    motorsEnabled = false;
    Serial.println("Emergency stop activated");
  }
  else if (action == "calibrate") {
    calibrateMotors();
  }
  else if (action == "get_status") {
    sendStatus();
  }
  else {
    // Regular movement commands
    int leftMotor = doc["left_motor"] | 0;
    int rightMotor = doc["right_motor"] | 0;
    float duration = doc["duration"] | 1.0;
    
    controlMotors(leftMotor, rightMotor);
    
    if (duration > 0) {
      delay(duration * 1000);
      stopMotors();
    }
  }
}

void controlMotors(int leftSpeed, int rightSpeed) {
  // Constrain speeds to valid range
  leftSpeed = constrain(leftSpeed, -255, 255);
  rightSpeed = constrain(rightSpeed, -255, 255);
  
  // Left motor control
  if (leftSpeed > 0) {
    digitalWrite(motor1Pin1, HIGH);
    digitalWrite(motor1Pin2, LOW);
  } else if (leftSpeed < 0) {
    digitalWrite(motor1Pin1, LOW);
    digitalWrite(motor1Pin2, HIGH);
    leftSpeed = -leftSpeed;
  } else {
    digitalWrite(motor1Pin1, LOW);
    digitalWrite(motor1Pin2, LOW);
  }
  analogWrite(motor1Enable, leftSpeed);
  
  // Right motor control
  if (rightSpeed > 0) {
    digitalWrite(motor2Pin1, HIGH);
    digitalWrite(motor2Pin2, LOW);
  } else if (rightSpeed < 0) {
    digitalWrite(motor2Pin1, LOW);
    digitalWrite(motor2Pin2, HIGH);
    rightSpeed = -rightSpeed;
  } else {
    digitalWrite(motor2Pin1, LOW);
    digitalWrite(motor2Pin2, LOW);
  }
  analogWrite(motor2Enable, rightSpeed);
  
  Serial.print("Motors: Left=");
  Serial.print(leftSpeed);
  Serial.print(", Right=");
  Serial.println(rightSpeed);
}

void stopMotors() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, LOW);
  analogWrite(motor1Enable, 0);
  analogWrite(motor2Enable, 0);
  Serial.println("Motors stopped");
}

void calibrateMotors() {
  Serial.println("Calibrating motors...");
  
  // Test left motor
  controlMotors(150, 0);
  delay(500);
  stopMotors();
  delay(200);
  
  // Test right motor
  controlMotors(0, 150);
  delay(500);
  stopMotors();
  delay(200);
  
  // Test both motors
  controlMotors(150, 150);
  delay(500);
  stopMotors();
  
  Serial.println("Motor calibration complete");
}

void sendStatus() {
  DynamicJsonDocument doc(512);
  doc["status"] = "ok";
  doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["ip_address"] = WiFi.localIP().toString();
  doc["motors_enabled"] = motorsEnabled;
  doc["uptime"] = millis();
  doc["free_heap"] = ESP.getFreeHeap();
  
  String response;
  serializeJson(doc, response);
  
  // Send to all connected clients (simplified)
  Serial.println("Status: " + response);
}

