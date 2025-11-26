#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ================= USER CONFIGURATION =================
const char* ssid = "devin";         // <--- ENTER WIFI NAME
const char* password = "qwertyui"; // <--- ENTER WIFI PASS

// ================= PIN DEFINITIONS =================
struct Motor {
  int pinEn;
  int pinIn1;
  int pinIn2;
};

// Motor 1 (Front Left)
Motor m1 = {17, 5, 4}; 

// Motor 2 (Front Right)
Motor m2 = {18, 7, 6};

// Motor 3 (Back Left)
Motor m3 = {3, 10, 11};

// Motor 4 (Back Right)
Motor m4 = {8, 13, 12};

// ================= SERVER SETUP =================
WebServer server(80);

// ================= MOTOR CONTROL LOGIC =================
void setMotorSpeed(Motor m, int speed) {
  
  // Constrain speed to valid PWM range
  int pwmValue = constrain(abs(speed), 0, 255);

  if (speed > 0) {
    // FORWARD
    digitalWrite(m.pinIn1, HIGH);
    digitalWrite(m.pinIn2, LOW);
    analogWrite(m.pinEn, pwmValue); 
  } 
  else if (speed < 0) {
    // REVERSE
    digitalWrite(m.pinIn1, LOW);
    digitalWrite(m.pinIn2, HIGH);
    analogWrite(m.pinEn, pwmValue);
  } 
  else {
    // STOP
    digitalWrite(m.pinIn1, LOW);
    digitalWrite(m.pinIn2, LOW);
    analogWrite(m.pinEn, 0);
  }
}

// Initialize pins AND force them to 0 immediately
void initMotor(Motor m) {
  pinMode(m.pinEn, OUTPUT);
  pinMode(m.pinIn1, OUTPUT);
  pinMode(m.pinIn2, OUTPUT);

  // SAFETY: Force inputs to Low immediately
  digitalWrite(m.pinIn1, LOW);
  digitalWrite(m.pinIn2, LOW);
  analogWrite(m.pinEn, 0);
}

// ================= HTTP HANDLER =================
void handleMotorCommand() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "Body not received");
    return;
  }

  String body = server.arg("plain");
  JsonDocument doc; 
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  // Parse speeds
  int s1 = doc["fl"]; 
  int s2 = doc["fr"];
  int s3 = doc["bl"];
  int s4 = doc["br"];

  // Apply speeds
  setMotorSpeed(m1, s1);
  setMotorSpeed(m2, s2);
  setMotorSpeed(m3, s3);
  setMotorSpeed(m4, s4);

  server.send(200, "application/json", "{\"status\":\"ok\"}");
  Serial.printf("Set Speeds -> FL:%d FR:%d BL:%d BR:%d\n", s1, s2, s3, s4);
}

// ================= MAIN SETUP =================
void setup() {
  Serial.begin(115200);
  delay(1000); // Give serial a moment to start

  Serial.println("Initializing Motors...");

  // Initialize and FORCE STOP all motors
  initMotor(m1);
  initMotor(m2);
  initMotor(m3);
  initMotor(m4);

  // Double check safety: Call the stop logic explicitly for all
  setMotorSpeed(m1, 0);
  setMotorSpeed(m2, 0);
  setMotorSpeed(m3, 0);
  setMotorSpeed(m4, 0);

  Serial.println("Motors Initialized and Halted.");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/move", HTTP_POST, handleMotorCommand);
  server.begin();
  Serial.println("HTTP Server started.");
}

void loop() {
  server.handleClient();
}