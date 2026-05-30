// LiDAR Maze Robot — Arduino Mega 2560
// Receives 77-byte binary frames from FPGA on Serial1 (pin 19 RX, pin 18 TX)
// Controls 4 DC motors via Adafruit Motor Shield v3 (I2C)
//
// Install: Adafruit Motor Shield V2 library via Library Manager

#include <Wire.h>
#include <Adafruit_MotorShield.h>

// ---------------------------------------------------------------
// Frame protocol constants (must match output_encoder.sv)
// ---------------------------------------------------------------
static const uint8_t  HDR0      = 0xAA;
static const uint8_t  HDR1      = 0x55;
static const int      FRAME_LEN = 77;
static const int      NUM_SECTS = 18;

// ---------------------------------------------------------------
// Navigation tuning
// ---------------------------------------------------------------
static const uint16_t WALL_THRESH  = 400;  // mm — wall is "present"
static const uint16_t CLEAR_THRESH = 500;  // mm — path is "open"
static const uint16_t STOP_THRESH  = 150;  // mm — emergency stop
static const int      BASE_SPEED   = 150;  // motor speed 0-255
static const int      TURN_SPEED   = 120;

// ---------------------------------------------------------------
// Sector layout: sector 0 = front (0°), clockwise
// Sector 4  ≈ right  (80°)
// Sector 9  ≈ rear   (180°)
// Sector 13 ≈ left   (260°)
// ---------------------------------------------------------------
#define SECT_FRONT  0
#define SECT_FRIGHT 2
#define SECT_RIGHT  4
#define SECT_REAR   9
#define SECT_LEFT   13
#define SECT_FLEFT  16

// ---------------------------------------------------------------
// Motor shield
// ---------------------------------------------------------------
Adafruit_MotorShield AFMS;
Adafruit_DCMotor    *motors[4];  // motors[0]=M1 ... motors[3]=M4

// Motor layout (viewed from above):
//   M1=front-left  M2=front-right
//   M3=rear-left   M4=rear-right

// ---------------------------------------------------------------
// Sector data
// ---------------------------------------------------------------
struct Sector {
  uint16_t avg_mm;
  uint16_t min_mm;
};
Sector   sectors[NUM_SECTS];
bool     emergency_stop;
bool     frame_ready;

// ---------------------------------------------------------------
// Serial1 parser state machine
// ---------------------------------------------------------------
enum ParserState {
  WAIT_HDR0,
  WAIT_HDR1,
  READ_ESTOP,
  READ_RSVD,
  READ_DATA,
  READ_CSUM
};

ParserState parser_state = WAIT_HDR0;
uint8_t     rx_buf[FRAME_LEN];
int         rx_idx;

void process_frame();

// ---------------------------------------------------------------
// setup
// ---------------------------------------------------------------
void setup() {
  Serial.begin(115200);   // debug to PC
  Serial1.begin(115200);  // from FPGA

  Serial.println("LiDAR Maze Robot starting...");

  AFMS = Adafruit_MotorShield();
  if (!AFMS.begin()) {
    Serial.println("ERROR: Motor Shield not found!");
    while (1);
  }

  for (int i = 0; i < 4; i++) {
    motors[i] = AFMS.getMotor(i + 1);
    motors[i]->setSpeed(0);
    motors[i]->run(RELEASE);
  }

  Serial.println("Motor shield OK. Waiting for FPGA data...");
}

// ---------------------------------------------------------------
// loop
// ---------------------------------------------------------------
void loop() {
  // Parse incoming bytes from FPGA
  while (Serial1.available()) {
    uint8_t b = Serial1.read();
    parse_byte(b);
  }

  if (frame_ready) {
    frame_ready = false;
    if (emergency_stop) {
      stop_all();
      Serial.print("ESTOP sectors<150mm:");
      for (int i = 0; i < NUM_SECTS; i++) {
        if (sectors[i].min_mm > 0 && sectors[i].min_mm < STOP_THRESH) {
          Serial.print(" s");
          Serial.print(i);
          Serial.print("=");
          Serial.print(sectors[i].min_mm);
        }
      }
      Serial.println();
    } else {
      navigate();
    }
  }
}

// ---------------------------------------------------------------
// Binary frame parser
// ---------------------------------------------------------------
void parse_byte(uint8_t b) {
  switch (parser_state) {
    case WAIT_HDR0:
      if (b == HDR0) parser_state = WAIT_HDR1;
      break;

    case WAIT_HDR1:
      if (b == HDR1) {
        parser_state = READ_ESTOP;
      } else {
        parser_state = WAIT_HDR0;  // resync
        if (b == HDR0) parser_state = WAIT_HDR1;
      }
      break;

    case READ_ESTOP:
      rx_buf[2]    = b;
      emergency_stop = (b != 0);
      parser_state = READ_RSVD;
      break;

    case READ_RSVD:
      rx_buf[3]    = b;
      rx_idx       = 4;
      parser_state = READ_DATA;
      break;

    case READ_DATA:
      rx_buf[rx_idx++] = b;
      if (rx_idx >= 76) {
        parser_state = READ_CSUM;
      }
      break;

    case READ_CSUM: {
      // Verify checksum: XOR of bytes 2..75
      uint8_t csum = 0;
      for (int i = 2; i < 76; i++) csum ^= rx_buf[i];

      if (csum == b) {
        // Decode sectors
        for (int i = 0; i < NUM_SECTS; i++) {
          int base = 4 + i * 4;
          sectors[i].avg_mm = ((uint16_t)rx_buf[base]     << 8) | rx_buf[base + 1];
          sectors[i].min_mm = ((uint16_t)rx_buf[base + 2] << 8) | rx_buf[base + 3];
        }
        frame_ready = true;
      } else {
        Serial.print("BAD CSUM: got=");
        Serial.print(b, HEX);
        Serial.print(" calc=");
        Serial.println(csum, HEX);
      }
      parser_state = WAIT_HDR0;
      break;
    }
  }
}

// ---------------------------------------------------------------
// Navigation: right-hand rule wall following
// ---------------------------------------------------------------
void navigate() {
  uint16_t front = sectors[SECT_FRONT].min_mm;
  uint16_t right = sectors[SECT_RIGHT].min_mm;
  uint16_t left  = sectors[SECT_LEFT].min_mm;

  // Use 0 (no data) as "very far"
  if (front == 0) front = 9999;
  if (right == 0) right = 9999;
  if (left  == 0) left  = 9999;

  Serial.print("F="); Serial.print(front);
  Serial.print(" R="); Serial.print(right);
  Serial.print(" L="); Serial.println(left);

  // Right-hand rule:
  //  1. If right wall present AND front clear → go forward
  //  2. If right wall absent → turn right (hug the wall)
  //  3. If front blocked → turn left
  //  4. Otherwise → go forward

  if (front < CLEAR_THRESH) {
    // Front is blocked
    if (left > CLEAR_THRESH) {
      turn_left();
    } else {
      // Boxed in — turn around
      turn_right();
    }
  } else if (right > WALL_THRESH) {
    // Lost right wall → turn right to find it
    turn_right();
  } else {
    // Right wall present, front open → go forward
    go_forward();
  }
}

// ---------------------------------------------------------------
// Omni-wheel kinematics
// Positive vx = forward, positive vy = right, positive omega = CW
// Motor layout:
//   M1=front-left  M2=front-right
//   M3=rear-left   M4=rear-right
// ---------------------------------------------------------------
void set_motors(int vx, int vy, int omega) {
  int m[4];
  m[0] =  vx - vy - omega;  // front-left
  m[1] =  vx + vy + omega;  // front-right
  m[2] =  vx + vy - omega;  // rear-left
  m[3] =  vx - vy + omega;  // rear-right

  for (int i = 0; i < 4; i++) {
    int spd = m[i];
    if (spd > 255)  spd = 255;
    if (spd < -255) spd = -255;

    motors[i]->setSpeed(abs(spd));
    if (spd > 0)      motors[i]->run(FORWARD);
    else if (spd < 0) motors[i]->run(BACKWARD);
    else              motors[i]->run(RELEASE);
  }
}

void go_forward()  { set_motors( BASE_SPEED, 0, 0); }
void go_backward() { set_motors(-BASE_SPEED, 0, 0); }
void turn_right()  { set_motors(0, 0,  TURN_SPEED); }
void turn_left()   { set_motors(0, 0, -TURN_SPEED); }
void stop_all() {
  for (int i = 0; i < 4; i++) motors[i]->run(BRAKE);
}
