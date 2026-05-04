// first algorithm -- find the most open direction and move towards it

struct Sector {
  int angle;
  int average;
  int minimum;
};

//added a new struct to split the angles into 4 quadrants
struct Quadrant {
  int startAngle;
  int endAngle;
  float averageScore;
};

Sector sectors[36];

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


// write makeDecision - temp by Akshay
int makeDecision(Sector sectors[36]) {
  int bestDirection = 0;
  //logic to find best direction
  //hint: sectors[i].average

  float bestScore = -1;

  for (int i = 0; i < 36; i++) {
    // Combine average and minimum into a single score (weighted equally)
    float score = (sectors[i].average + sectors[i].minimum) / 2.0;

    if (score > bestScore) {
      bestScore = score;
      bestDirection = sectors[i].angle;
    }
  }

  return bestDirection;
}

//Converts 36 quadrents into 4 sectors
void computeQuadrants(Sector sectors[36], Quadrant quads[4]){
  for (int q = 0; q < 4; q++){ //loop through 4 quadrants first(1-4)
    int startIndex = q * 9;
    int endIndex = startIndex + 9;

    float totalScore = 0;
  

    for (int i = startIndex; i < endIndex ; i++){ //loop through each indiidual (0-8, 9-17, 18-26, 27-35)
    
      float score = (sectors[i].average + sectors[i].minimum) / 2.0; //converts average and minimum
                                                                       //into a single score
      totalScore += score;
    
    }

    quads[q].startAngle = sectors[startIndex].angle;
    quads[q].endAngle = sectors[endIndex - 1].angle;
    quads[q].averageScore = totalScore / 9.0;


  }
}

//takes in the already processed 4 sectors and finds the best one
int bestQuadrant(Quadrant quads[4]){
  int best = 0;
  float bestScore = -1;

  for (int i = 0; i < 4; i ++){
    if (quads[i].averageScore > bestScore){
      bestScore = quads[i].averageScore;
      best = i;
    }
  }
  return best;
}
 
// motor direction - test
void setup() {
  Serial.begin(115200);

  Quadrant quads[4];
  computeQuadrants(sectorsTest, quads);
  int bestQ = bestQuadrant(quads);


  Serial.print("Best Quadrant: ");
  Serial.println(bestQ);
  Serial.print("Angle Range: ");
  Serial.print(quads[bestQ].startAngle);
  Serial.print(" to ");
  Serial.println(quads[bestQ].endAngle);
}

void loop() {
  // FPGA reading TBA 
}
