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


void Move(int Time, int Bearing){
  //enter bearing as degrees so (00)0-360, if it's -1 it will be to stop. Time should be kept low
  if(Bearing == -1){
    Motor1->run(4);
    Motor2->run(4);
    Motor3->run(4);
    Motor4->run(4);
  }
  else{
    Bearing = Bearing * (acos(-1.0) / 180); //converts bearing from degrees to radians

    Motor1->setSpeed(M1Sp*cos(Bearing));
    Motor1->run(Bearing);
    Motor3->setSpeed(M3Sp*cos(Bearing));
    Motor3->run(Bearing);
    Motor2->setSpeed(M2Sp*sin(Bearing));
    Motor2->run(Bearing);
    Motor4->setSpeed(M4Sp*sin(Bearing));
    Motor4->run(Bearing);
    delay(Time);
  }


}


int Forwards_Direction = 0; // forward direction is a 0-35 value, same order as lidar scan
int min_Distance = 700; // min distance is the minimum distance the car should stay from the wall
int max_Distance = 1000; // max distance is the maximum distance the car should stay from the wall
int bestDirection;
float bestScore;

void ScanMin(Sector sectors[36], int direction){ //ScanMin alters 2 global values, first value is the direciton bestDirection, second one is the score/distance bestScore
  bestDirection = -1;
  bestScore = 9000.0;
  int CurrDirec;
  float score = 0.0;

  for (int j = -4; j < 5; j++) {
    CurrDirec = (direction + j + 9) % 36;

    score = (sectors[CurrDirec].average + sectors[CurrDirec].minimum) / 2.0;

    if (score < bestScore) {
      bestScore = score;
      bestDirection = CurrDirec;
    }
  }

  if(bestDirection == -1){ //a stupid fix just in case something really stupid happens
    bestDirection = direction;
    bestScore = score;
  }
}

// make decision returns 0-35 for bearing directions, going clockwise around and 0 is "forwards" on the lidar.
int makeDecision(Sector sectors[36]) {
  
  bool Turn = true; //turn is a loop used in case the forwards direction needs to be changed (i.e. turning right or left (or i turn, which is 2 left turns))

  //for right turns, there's no loop as there shouldn't be successive right turns (no rightward U turns)
  ScanMin(sectors[36], (Forwards_Direction + 9) % 36);
  if(bestScore > max_Distance){ //if it gets too far from the wall, it just starts moving towards the wall. This way is better for accounting for both cases of 1. it's a straight wall and it got too far away, and 2. it's a right turn
    Forwards_Direction = (Forwards_Direction + 9) % 36;
  }else{
    while(Turn){ //for left turns; if the car just did a right turn, it shouldn't need to do a left turn (reverse what it just did)
      //checks if the "front" wall is close enough, if so do a "left" turn
      ScanMin(sectors[36], Forwards_Direction);
      if(bestScore < max_Distance){ //if forwards direction is too close, turn left
        Forwards_Direction = (Forwards_Direction + 27) % 36;
      }else{
        Turn = false;
      }
    }
  }

  ScanMin(sectors[36], (Forwards_Direction + 9) % 36); //scans right side wall to see closest point
  Forwards_Direction = (bestDirection + 27) % 36; //sets the forwards direction to 90 degrees left from the direction of shortest distance from the wall
  
  if(bestScore < min_Distance){ //if the car is too close to the wall, turn slightly (10 degrees) left
    Forwards_Direction = (bestDirection + 35) % 36;
  }

  return Forwards_Direction;

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


  int decision; //is decision reduntant, since output's just 'Forwards_Direction'?
  decision = makeDecision(sectorsTest);

  Serial.print("best direction:");
  Serial.println(decision);

  Move(1000, decision); //moves forwards 1 second in the direction of the decision
  Move(1, -1); //stops motors since this is just a test section and without it, it will just continue spinning

}

void loop() {
  // FPGA reading TBA 
}
