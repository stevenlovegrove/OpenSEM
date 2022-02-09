#pragma once

#include "serial_controller.h"

#include <cmath>
#include <array>

class VacuumController
{
public:
    VacuumController(std::string port)
        : controller(6,""), current_pressure(std::numeric_limits<double>::quiet_NaN())
    {
        controller.connection_changed.connect([&](EventConnection e){
            if(e.connected) {
                std::cout << "[connected] Vacuum Controller" << std::endl;
            }else{
                std::cout << "[Disconnected] Vacuum Controller" << std::endl;
                current_pressure = std::numeric_limits<double>::quiet_NaN();
            }
        });
        controller.on_unprompted_message.connect(&VacuumController::process_message, this);
        controller.connect(port, 9600);
    }

    ~VacuumController()
    {
        idle();
    }

    bool is_connected()
    {
        return controller.is_connected();
    }

    const double& pressure() const
    {
        return current_pressure;
    }

    void idle()
    {
        controller.send("==");
    }

    void rough()
    {
        controller.send("<<");
    }

    void turbo()
    {
        controller.send("<+");
    }

    void vent()
    {
        controller.send(">+");
    }

    void calibrate_atmospheric()
    {
        controller.send("CA");
    }

    sigslot::signal<double> on_pressure_reading_torr;

private:
    void process_message(EventUnpromptedMessage mesg)
    {
        if(mesg.data.size() > 0) {
            if(mesg.data[0] == 'P' && mesg.data.size() == 6) {
                const float f = *((float*)&(mesg.data[1]));
                current_pressure = f;
                on_pressure_reading_torr(f);
            }
        }
    }

    double current_pressure;
    SerialController controller;
};
