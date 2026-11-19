// first algorithm -- find the most open direction and move towards it

struct Sector {
  int angle;
  int average;
  int minimum;
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


// write makeDecision 
int makeDecision(Sector sectors[36]) {
  int bestDirection = 0;
  //logic to find best direction
  //hint: sectors[i].average
  return bestDirection;
}
 
// motor direction - test
void setup() {
  Serial.begin(115200);

  int decision = makeDecision(sectorsTest); 

  Serial.print("best direction:");
  Serial.println(decision);
}

// ── Serial parser state (used by loop) ──────────────────────────────────────
enum ParseState { WAIT_BEGIN, READ_DATA };
static ParseState parseState = WAIT_BEGIN;
static int        sectorIdx  = 0;
static Sector     incoming[36];   // staging buffer — copied to sectors[] only on complete frame

void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();   // strip \r on Windows line endings

  switch (parseState) {

    case WAIT_BEGIN:
      if (line == "BEGIN") {
        sectorIdx  = 0;
        parseState = READ_DATA;
      }
      break;

    case READ_DATA:
      if (line == "BEGIN") {
        // New frame started before previous one finished — reset
        sectorIdx = 0;

      } else if (line == "END") {
        if (sectorIdx == 36) {
          // Complete frame received — commit and decide
          memcpy(sectors, incoming, sizeof(sectors));
          int decision = makeDecision(sectors);
          Serial.print("best direction:");
          Serial.println(decision);
        }
        parseState = WAIT_BEGIN;
        sectorIdx  = 0;

      } else if (sectorIdx < 36) {
        // Parse "angle,avg,min"
        int comma1 = line.indexOf(',');
        int comma2 = line.indexOf(',', comma1 + 1);

        if (comma1 > 0 && comma2 > comma1) {
          incoming[sectorIdx].angle   = line.substring(0, comma1).toInt();
          incoming[sectorIdx].average = line.substring(comma1 + 1, comma2).toInt();
          incoming[sectorIdx].minimum = line.substring(comma2 + 1).toInt();
          sectorIdx++;
        } else {
          // Malformed line — abort frame
          parseState = WAIT_BEGIN;
          sectorIdx  = 0;
        }

      } else {
        // Too many data lines without END — abort frame
        parseState = WAIT_BEGIN;
        sectorIdx  = 0;
      }
      break;
  }
}
