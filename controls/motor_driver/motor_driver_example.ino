/* Motor Driver Code Outline */
// Libraries for Motor
#include <Wire.h>
#include <Adafruit_MotorShield.h> // Must add libary - see MotorShield Manual
//https://cdn-learn.adafruit.com/downloads/pdf/adafruit-motor-shield-v2-for-arduino.pdf

// Initialize Motors
Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_DCMotor *Motor1 = AFMS.getMotor(1); // Motors can be switched here (1) <--> (2)
Adafruit_DCMotor *Motor2 = AFMS.getMotor(2);

// Set Initial Speed of Motors (CAN BE EDITED BY USER)
//  initial speed may vary and later can be changed with Sp potentiometer. theoretical max
//  is 255, but the motors will likely overdraw power and cause the Arduino to shut off. 
//  motors likely need a minimum speed of 20-30 to move the cart.
//
//  motor speeds are separated incase one motor turns faster than the other.  
int M1Sp = 60; 
int M2Sp = 60;

//Set LED Pin
// TODO: Replace "___", and assign the pin number connected to the Arduino.
//  it is recommended to use pin 13, but can change to another digital pin 
//  and connect extra LED to me more easily seen
int led_Pin = ___; 

// setup - runs once
void setup(){
  Serial.begin(___); // TODO: Replace "___", and input the baud rate for serial communication
  AFMS.begin(); // initialize the motor
  
  pinMode(___, ___); // TODO: Replace "___", and set the led_pin to be an output

    // Gives you a moment before cart actually moves
    for (int waitii = 0; waitii < 20; waitii++) {
      digitalWrite(___, ___); // TODO: Replace "___", and turn on the LED
      delay(100); // wait for 100 milliseconds

      digitalWrite(___, ___); // TODO: Replace "___", and turn off the LED
      delay(100); // wait for 100 milliseconds
    } 
}

// loop - loops forever
void loop(){ 
// applicable motor keywords:
//    FORWARD   - run the motors in the forwards direction
//    BACKWARD  - run the motors in the backwards direction
//    RELEASE   - stop the motors from turning

  // TODO: Start Motors in forward direction
    Motor1->setSpeed(___); // TODO: Replace "___", and set the speed of motor 1
    Motor1->run(___); // TODO: Replace "___", and set the direction of motor 1
    Motor2->setSpeed(___); // TODO: Replace "___", and set the speed of motor 2
    Motor2->run(___); // TODO: Replace "___", and set the direction of motor 2
  delay(3000); // let run forward for 3 seconds
  
  // TODO: Start Motors in backward direction
    Motor1->setSpeed(___); // TODO: Replace "___", and set the speed of motor 1
    Motor1->run(___); // TODO: Replace "___", and set the direction of motor 1
    Motor2->setSpeed(___); // TODO: Replace "___", and set the speed of motor 2
    Motor2->run(___); // TODO: Replace "___", and set the direction of motor 2
  delay(3000); // let run backward for 3 seconds 
  
  // TODO: Stop Motors
    Motor1->setSpeed(___); // TODO: Replace "___", and set the speed of motor 1
    Motor1->run(___); // TODO: Replace "___", and set the direction of motor 1
    Motor2->setSpeed(___); // TODO: Replace "___", and set the speed of motor 2
    Motor2->run(___); // TODO: Replace "___", and set the direction of motor 2
  delay(3000); // stop for 3 seconds 
}
