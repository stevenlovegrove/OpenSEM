#include <Arduino.h>
#include <AD5254_asukiaaa.h>

constexpr int CMD_LEN = 2;
constexpr char CMD_HV_ON[]  = "!!";
constexpr char CMD_HV_OFF[] = "..";
constexpr char CMD_SET_VOLTAGE[] = "Vx"; // V char followed by byte [0,255] representing range 0 - 30 kv

constexpr uint8_t PIN_RELAY_HV = A2; 
// constexpr uint8_t PIN_RELAY_SPARE = A6; 

constexpr uint8_t POT_HV_CH = 0;
constexpr uint8_t POT_HV_DFT = 0;

#define serial_pc Serial

AD5254_asukiaaa pot(AD5254_ASUKIAAA_ADDR_A0_GND_A1_GND);

void report_error(const char* err)
{
  serial_pc.write('!');
  serial_pc.write(err);
  serial_pc.write('\n');
}

void high_voltage_enable(bool enable)
{
  digitalWrite(PIN_RELAY_HV, !enable);
}

void set_voltage(uint8_t v)
{
  pot.writeRDAC(POT_HV_CH,v);
}

void process_pc_command()
{
  char cmd[CMD_LEN];
  const size_t bytes_read = serial_pc.readBytes(cmd, CMD_LEN);

  if(bytes_read == CMD_LEN) {
    if( !strncmp(cmd, CMD_HV_ON, CMD_LEN) ) {
      high_voltage_enable(true);
      serial_pc.println("ON");
    }else if( !strncmp(cmd, CMD_HV_OFF, CMD_LEN) ) {
      high_voltage_enable(false);
      serial_pc.println("OFF");
    }else if(cmd[0] == 'V') {
      const uint8_t R = cmd[1];
      set_voltage(R);
      const unsigned v = uint32_t(R) * 30000 / 256;
      serial_pc.print("V=");
      serial_pc.println(v);
    }else{
      report_error("unknown command");
      serial_pc.print(cmd);
    }
  }else{
    report_error("unexpected message");
  }
}

void setup_pot()
{
  pot.begin();
  uint8_t ch0_dft = 255;
  if(!pot.loadEEPROM(POT_HV_CH, &ch0_dft)) {
    if(ch0_dft != 0) {
      if(!pot.saveEEPROM(POT_HV_CH, POT_HV_DFT)) {
        serial_pc.println("Updated EEPROM default");
      }else{
        report_error("Unable to write EEPROM");
      }
    }
  }else{
    report_error("Unable to read EEPROM");
  }
}

void setup() {
  // Make sure we start with HV off.
  high_voltage_enable(false);
  pinMode(PIN_RELAY_HV, OUTPUT);

  // Initiate serial comms
  serial_pc.begin(9600);

  setup_pot();
  set_voltage(0);
}

void loop() {
  if(serial_pc.available()) {
    process_pc_command();
  }

  delay(100);
}