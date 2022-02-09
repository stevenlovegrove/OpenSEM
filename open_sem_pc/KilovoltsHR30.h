#pragma once

#include "serial_controller.h"

class KilovoltsHR30
{
public:
    KilovoltsHR30(std::string port)
        : voltage_setting(0), is_hv_on(false)
    {
        controller.connection_changed.connect([&](EventConnection e){
            if(e.connected) {
                std::cout << "[connected] Kilovolts HR30 Arduino" << std::endl;
                idle();
            }else{
                std::cout << "[Disconnected] Kilovolts HR30 Arduino" << std::endl;
            }
        });
        controller.connect(port, 9600);
    }

    ~KilovoltsHR30()
    {
        idle();
    }

    bool is_connected()
    {
        return controller.is_connected();
    }

    bool is_high_voltage_on()
    {
        return is_hv_on;
    }

    void idle()
    {
        set_on_off(false);
        set_voltage(0);
    }

    void set_on_off(bool enable)
    {
        if(enable) {
            controller.send_and_retrieve("!!");
        }else{
            controller.send_and_retrieve("..");
        }

        is_hv_on = enable;
    }

    void set_voltage(uint8_t voltage)
    {
        std::string packet('\0', 2);
        packet[0] = 'V';
        packet[1] = static_cast<char>(voltage);
        controller.send(packet);

        voltage_setting = voltage;
    }

    double get_voltage()
    {
        return (voltage_setting) / 58.0 * 10000.0;
    }

    bool is_hv_on;
    uint8_t voltage_setting;
    SerialController controller;
};
