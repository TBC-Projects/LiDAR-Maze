#include <Adafruit_MotorShield.h>

/* Motor Driver Code Outline */
// Libraries for Motor
#include <Wire.h>
#include <Adafruit_MotorShield.h> // Must add libary - see MotorShield Manual
//https://cdn-learn.adafruit.com/downloads/pdf/adafruit-motor-shield-v2-for-arduino.pdf

// Initialize Motors

/*Motor order: starting from the "left" side, going anti-clockwise: 1,2,3,4
  4
  ^
1 | 3
  |
  2
*/

Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_DCMotor *Motor1 = AFMS.getMotor(1); // Motors can be switched here (1) <--> (2)
Adafruit_DCMotor *Motor2 = AFMS.getMotor(2);
Adafruit_DCMotor *Motor3 = AFMS.getMotor(3);
Adafruit_DCMotor *Motor4 = AFMS.getMotor(4);

// Set Initial Speed of Motors (CAN BE EDITED BY USER)
//  initial speed may vary and later can be changed with Sp potentiometer. theoretical max
//  is 255, but the motors will likely overdraw power and cause the Arduino to shut off. 
//  motors likely need a minimum speed of 20-30 to move the cart.
//
//  motor speeds are separated incase one motor turns faster than the other.  
int M1Sp = 60; 
int M2Sp = 60;
int M3Sp = 60; 
int M4Sp = 60;

//Set LED Pin
// TODO: Replace "___", and assign the pin number connected to the Arduino.
//  it is recommended to use pin 13, but can change to another digital pin 
//  and connect extra LED to me more easily seen
int led_Pin = 13;

`
// setup - runs once
void setup(){
  Serial.begin(9600); // TODO: Replace "___", and input the baud rate for serial communication
  AFMS.begin(); // initialize the motor
  
  pinMode(led_Pin, OUTPUT); // TODO: Replace "___", and set the led_pin to be an output

    // Gives you a moment before cart actually moves
    for (int waitii = 0; waitii < 20; waitii++) {
      digitalWrite(led_Pin, HIGH); // TODO: Replace "___", and turn on the LED
      delay(100); // wait for 100 milliseconds

      digitalWrite(led_Pin, LOW); // TODO: Replace "___", and turn off the LED
      delay(100); // wait for 100 milliseconds
    } 
}

//the input for Direction is an integer (1-4) as defined from the database

//1 -> FORWARD
//2 -> BACKWARD
//3 -> BRAKE
//4 -> RELEASE

// applicable motor keywords:
//    FORWARD   - run the motors in the forwards direction
//    BACKWARD  - run the motors in the backwards direction
//    RELEASE   - stop the motors from turning

void Forw_Back(int Time, int Direction){
    Motor1->setSpeed(M1Sp);
    Motor1->run(Direction);
    Motor3->setSpeed(M3Sp);
    Motor3->run(Direction);
  delay(Time);
}

void Right_Left(int Time, int Direction){
    Motor2->setSpeed(M2Sp);
    Motor2->run(Direction);
    Motor4->setSpeed(M4Sp);
    Motor4->run(Direction);
  delay(Time);
}

// loop - loops forever
void loop(){ 

  Forw_Back(5000, 1);
  Forw_Back(5000, 2);
  Forw_Back(1000, 4);
  Right_Left(5000, 1);
  Right_Left(5000, 2);
  Right_Left(1000, 4);
  
}`