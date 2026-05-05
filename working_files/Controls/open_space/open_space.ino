#include <Wire.h>
#include <Adafruit_MotorShield.h> 


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
int MSp = 60; // MSp is a "generic" speed

//Set LED Pin
// TODO: Replace "___", and assign the pin number connected to the Arduino.
//  it is recommended to use pin 13, but can change to another digital pin 
//  and connect extra LED to me more easily seen
int led_Pin = 13;

struct Sector {
  int angle;
  int average;
  int minimum;
};

Sector sectorsTest[36] = {
  {0, 2500, 2450},    {10, 2500, 2480},   {20, 2500, 2470},   // Front - OPEN
  {30, 2500, 2490},   {40, 2500, 2460},   {50, 2500, 2475},   
  {60, 1500, 1450},   {70, 1200, 1150},   {80, 800, 750},     // Right side - wall getting closer
  {90, 800, 775},     {100, 800, 780},    {110, 800, 770},    // Right - WALL
  {120, 800, 785},    {130, 800, 775},    {140, 1200, 1150},  
  {150, 1500, 1480},  {160, 2000, 1950},  {170, 2500, 2470},  
  {180, 2500, 2480},  {190, 2500, 2460},  {200, 2500, 2475},  // Behind - OPEN
  {210, 2500, 2490},  {220, 2000, 1960},  {230, 1500, 1470},  
  {240, 1200, 1180},  {250, 800, 780},    {260, 800, 770},    // Left - WALL
  {270, 800, 785},    {280, 800, 775},    {290, 800, 780},    
  {300, 800, 770},    {310, 1200, 1170},  {320, 1500, 1450},  
  {330, 2000, 1970},  {340, 2500, 2460},  {350, 2500, 2480}
};



//the input for Direction is an integer (1-4) as defined from the database

//1 -> FORWARD
//2 -> RIGHT
//3 -> BACK
//4 -> LEFT
//0 -> BRAKE


void Move(int Time, int Direction){
  if(Direction == 0){
    Motor1->run(4);
    Motor2->run(4);
    Motor3->run(4);
    Motor4->run(4);
  }
  else{
    bool Front_Right = Direction % 2 == 1;
    Direction = 1 + int(Direction>=3);
    if(Front_Right){
      Motor1->setSpeed(M1Sp);
      Motor1->run(Direction);
      Motor3->setSpeed(M3Sp);
      Motor3->run(Direction);
      delay(Time);
    }

    else{
      Motor2->setSpeed(M2Sp);
      Motor2->run(Direction);
      Motor4->setSpeed(M4Sp);
      Motor4->run(Direction);
      delay(Time);
    }
  }


}

// make decision returns 0-3 for cordinal directions, 0 is front and clockwise around.
int makeDecision(Sector sectors[36], int oldDirection) {
  int bestDirection = 0;

  float bestScore = -1;

  for (int i = 0; i < 4; i++) {
    float score = 0;
    
    for (int j = -4; j < 5; i++) {
      k = (9*i + j + 36) % 36
      score += (sectors[k].average + sectors[k].minimum) / 2.0;

      if (score > bestScore && i != oldDirection) {
        bestScore = score;
        bestDirection = i;
      }
  
    }

    if (bestDirection == -1){
      bestDirection == (oldDirection + 2) % 4;
    }

  }
  
  Move(int(score / MSp * 1), bestDirection + 1);
  return bestDirection;
}





 
// motor direction - test
void setup() {
  Serial.begin(9600);
  AFMS.begin();
  
  pinMode(led_Pin, OUTPUT);

    for (int waitii = 0; waitii < 20; waitii++) {
      digitalWrite(led_Pin, HIGH);
      delay(100);

      digitalWrite(led_Pin, LOW);
      delay(100);
    } 


  int decision = 2;
  decision = makeDecision(sectorsTest, decision);

  Serial.print("best direction:");
  Serial.println(decision);



}

void loop() {
  // FPGA reading TBA 
}
