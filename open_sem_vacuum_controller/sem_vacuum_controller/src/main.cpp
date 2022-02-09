#include <Arduino.h>

#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
 #include <avr/power.h> // Required for 16 MHz Adafruit Trinket
#endif

#define PIN        4
#define NUMPIXELS 12
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

constexpr float ADC_MAX = 2^10;
constexpr unsigned long REPORT_INTERVAL_MS = 1000;

constexpr int CMD_LEN = 2;
constexpr char CMD_IDLE[]  = "==";
constexpr char CMD_ROUGH[] = "<<";
constexpr char CMD_PUMP[]  = "<+";
constexpr char CMD_VENT[]  = ">>";
constexpr char CMD_FAST_VENT[]  = ">+";
constexpr char CMD_AUTO_ON[]  = "a+";
constexpr char CMD_AUTO_OFF[]  = "a-";
constexpr char CMD_ATM_CALIB[]  = "CA";

constexpr char REPORT_PRESSURE_TORR = 'P';
constexpr char REPORT_ATM_CALIB_DONE = 'A';
constexpr char REPORT_ERROR = '!';
constexpr char REPORT_END = '\n';

constexpr uint8_t PIN_ROUGHING_START = 5;  // OUT: HIGH to power rotary pump

constexpr uint8_t PIN_TURBO_STATUS   = 3;  // IN: HIGH IFF > 80% full speed
constexpr uint8_t PIN_TURBO_SPEED    = A0; // IN: Analog 0 to VCC - proportion of full speed
constexpr uint8_t PIN_TURBO_START    = 6;  // OUT: HIGH to spin

constexpr uint8_t PIN_VENT_OPEN      = 7;  // OUT: HIGH to open vent

// serial port definitions
#define serial_pc Serial
#define serial_pressure Serial1

// time last report was provided to PC
unsigned long time_last_status = 0;

bool auto_transitions = false;

float progress = 0.0;

constexpr float LOG_ATM_PRESSURE = 6.63331843328; // ln(760);
float current_pressure = 0.0;
float log_current_pressure = 0.0;

enum class Mode
{
  idle,
  roughing,
  pumping,
  venting,
  fast_vent,
};

enum class EGaugeQuery
{
  PR4,
  ATM,
  None
};

const char* SGaugeQuery[] = {
  "PR4",
  "ATM",
  ""
};

Mode current_mode = Mode::idle;
EGaugeQuery current_query = EGaugeQuery::None;

////////////////////////////////////////////////////////////
// Utils
////////////////////////////////////////////////////////////

template<typename S, typename T>
void serialize(S& sp, const T& x)
{
  sp.write((char*)&x,sizeof(T));
}

template<typename S, typename T1, typename T2, typename... Args>
void serialize(S& sp, const T1& x1, const T2& x2, Args... xs)
{
  serialize<S,T1>(sp, x1);
  serialize(sp, x2,xs...);
}

void report_error(const char* err)
{
  serialize(serial_pc, REPORT_ERROR);
  serial_pc.write(err);
  serialize(serial_pc, REPORT_END);
}

////////////////////////////////////////////////////////////
// Raw Device Control
////////////////////////////////////////////////////////////

void roughing_pump_enable(bool enable)
{
  digitalWrite(PIN_ROUGHING_START, enable);
}

void turbo_pump_enable(bool enable)
{
  digitalWrite(PIN_TURBO_START, !enable);
}

float turbo_pump_get_speed()
{
  const int adc = analogRead(PIN_TURBO_SPEED);
  return adc / ADC_MAX;
}

void vent_enable(bool enable)
{
  digitalWrite(PIN_VENT_OPEN, !enable);
}

void calibrate_atmospheric()
{
  // TODO: communicate with pressure sensor to set atmospheric calibration
}

////////////////////////////////////////////////////////////
// Mode Switches
////////////////////////////////////////////////////////////

void start_idle()
{
  current_mode = Mode::idle;
  roughing_pump_enable(false);
  turbo_pump_enable(false);
  vent_enable(false);
  progress = 0.0;
}

void start_roughing()
{
  current_mode = Mode::roughing;
  vent_enable(false);
  roughing_pump_enable(true);
  progress = 0.0;
}

void start_pumping()
{
  if(current_mode != Mode::roughing) {
    report_error("Can only start pumping from roughing state");
    return;
  }

  current_mode = Mode::pumping;
  turbo_pump_enable(true);
  progress = 0.0;
}

void start_vent()
{
  // stop any pumps and begin pressure limited venting
  current_mode = Mode::venting;
  roughing_pump_enable(false);
  turbo_pump_enable(false);
  progress = 0.0;
}

void start_fast_vent()
{
  // stop any pumps and begin pressure limited venting
  current_mode = Mode::fast_vent;
  roughing_pump_enable(false);
  turbo_pump_enable(false);
  vent_enable(true);
  progress = 0.0;
}

////////////////////////////////////////////////////////////
// State Machine
////////////////////////////////////////////////////////////

void send_gauge_query(EGaugeQuery query, uint8_t addr = 254)
{
  char buffer[24];
  snprintf(buffer, sizeof(buffer), "@%03d%s?;FF", addr, SGaugeQuery[(int)query]);
  current_query = query;
  serial_pressure.print(buffer);
}

void send_gauge_cmd(EGaugeQuery query, const char* arg, uint8_t addr = 254)
{
  char buffer[24];
  snprintf(buffer, sizeof(buffer), "@%03d%s!%s;FF", addr, SGaugeQuery[(int)query], arg);
  current_query = query;
  serial_pressure.print(buffer);
}

void process_gauage_ack(char* args)
{
  if(current_query == EGaugeQuery::PR4) {
    current_pressure = atof(args);
    log_current_pressure = log(current_pressure + 1.0);
    serialize(serial_pc, REPORT_PRESSURE_TORR, current_pressure, REPORT_END);
    // serial_pc.print("Pressure: ");
    // serial_pc.print(args);
    // serial_pc.println(" Torr");
  }else if(current_query == EGaugeQuery::ATM) {
    serialize(serial_pc, REPORT_ATM_CALIB_DONE, REPORT_END);
    // serial_pc.println("ATM ACK'ed");
    // serial_pc.println(args);
  }else{
    report_error("Unexpected Guage Response");
  }

  current_query = EGaugeQuery::None;
}

void process_gauage_nak(char* args)
{
  int i = atoi(args);
  report_error("NAK");
  current_query = EGaugeQuery::None;
}

void process_pressure_message()
{
  int c = serial_pressure.read();
  if( c == '@') {
    char buffer[24];
    const int l = serial_pressure.readBytesUntil(';', buffer, 24);
    if(l) {
      buffer[l] = '\0';
      char ff[2];
      int l2 = serial_pressure.readBytes(ff,2);      

      if(l2 == 2 && ff[0] == 'F' && ff[1] == 'F') {
        char* acknak = buffer;
        while(isdigit(*acknak)) ++acknak;

        if(acknak[0] == 'A' && acknak[1] == 'C' && acknak[2] == 'K') {
          process_gauage_ack(acknak+3);
        }else if(buffer[0] == 'N' && buffer[1] == 'A' && buffer[2] == 'K') {
          process_gauage_nak(acknak+3);
        }else{
          report_error("Unexpected guage Response");
        }
      }else{
        report_error("Unexpected guage Prefix");
      }
    }else{
      report_error("No data from guage after start");
    }
  }else{
    // error
    serial_pc.println("Unexpected guage starting charector");
  }
}

void process_pc_command()
{
  char cmd[CMD_LEN];
  const size_t bytes_read = serial_pc.readBytes(cmd, CMD_LEN);

  if(bytes_read == CMD_LEN) {
    if( !strncmp(cmd, CMD_IDLE, CMD_LEN) ) {
      start_idle();
    }else if( !strncmp(cmd, CMD_ROUGH, CMD_LEN) ) {
      start_roughing();
    }else if( !strncmp(cmd, CMD_PUMP, CMD_LEN) ) {
      start_pumping();
    }else if( !strncmp(cmd, CMD_VENT, CMD_LEN) ) {
      start_vent();
    }else if( !strncmp(cmd, CMD_FAST_VENT, CMD_LEN) ) {
      start_fast_vent();
    }else if( !strncmp(cmd, CMD_AUTO_ON, CMD_LEN) ) {
      auto_transitions = true;
    }else if( !strncmp(cmd, CMD_AUTO_OFF, CMD_LEN) ) {
      auto_transitions = false;
    }else if( !strncmp(cmd, CMD_ATM_CALIB, CMD_LEN) ) {
      send_gauge_cmd(EGaugeQuery::ATM, "7.60E+2");    
    }else{
      report_error("unknown command");
      Serial.print(cmd);
    }
  }else{
    report_error("unexpected message");
  }
}

void send_pc_report()
{
  send_gauge_query(EGaugeQuery::PR4);
  time_last_status = millis();
}

////////////////////////////////////////////////////////////
// Main 
////////////////////////////////////////////////////////////

void setup_io()
{
  pinMode(PIN_ROUGHING_START, OUTPUT);
  pinMode(PIN_TURBO_STATUS, INPUT);
  pinMode(PIN_TURBO_SPEED, INPUT);
  pinMode(PIN_TURBO_START, OUTPUT);
  pinMode(PIN_VENT_OPEN, OUTPUT);
  
  // Communication with PC
  serial_pc.begin(9600);

  // Communication with pressure guage
  serial_pressure.begin(9600);
}

void setup() {
  setup_io();
  start_idle();
  pixels.begin();
  pixels.setBrightness(20);
}

void rainbow() {
  for(long firstPixelHue = 0; firstPixelHue < 5*65536; firstPixelHue += 256) {
    for(int i=0; i<pixels.numPixels(); i++) { 
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
    }
    pixels.show();
  }
}

void progress_bar(long hue, float progress, uint8_t brightness)
{
    float pix_lit = progress * pixels.numPixels();

    for(uint16_t i=0; i < pixels.numPixels(); i++) {
      float val = pix_lit - i;
      if(val > 0) {
        uint8_t v = val > 1.0 ? 255 :  uint8_t( val * brightness);
        pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(hue, 255, v)));
      }else{
        pixels.setPixelColor(i, pixels.Color(0,0,0) );
      }
    }
    pixels.show();
}

void throb(long hue, float progress)
{
  const float v = progress < 0.5 ? progress : 1.0 - progress;
  for(uint16_t i=0; i < pixels.numPixels(); i++) {
    pixels.setPixelColor(i, pixels.ColorHSV(hue, 255, uint8_t(v*255.0) ));
  }
  pixels.show();
}

void loop() {
  if(serial_pc.available()) {
    process_pc_command();
  }

  if(serial_pressure.available()) {
    process_pressure_message();
  }

  switch (current_mode)
  {
  case Mode::idle:
    // NO-OP
    throb(20000, progress);
    progress += 0.004;
    if(progress >= 1.0) progress = 0.0;
    break;
  case Mode::roughing:
    progress = min(1.0, max(0.0, 1.0 - log_current_pressure / LOG_ATM_PRESSURE));
    progress_bar(20000, progress, 255);

    if(auto_transitions) {
      // TODO: transition to pumping at target pressure
      if(progress >= 1.0) start_pumping();
    }
    break;
  case Mode::pumping:
    progress_bar(32767, progress, 255);
    progress += 0.001;

    if(auto_transitions) {
      // TODO: Turn pumps on and off over threshold final pressure
    }
    break;
  case Mode::venting:
    // Maintain venting ramp by toggling solenoid and watching pressure.
    if(auto_transitions) {
      // TODO: Transition to IDLE once at atmospheric
    }
    break;
  case Mode::fast_vent:
    progress_bar(50000, 1.0 - progress, 255);
    progress += 0.001;

    // This is basically overriding any vent logic in venting to open the vent valve
    if(auto_transitions) {
      // TODO: Transition to IDLE once at atmospheric
    }
    break;
  }

  if(millis() - time_last_status > REPORT_INTERVAL_MS) {
    send_pc_report();
  }

  delay(10);
}