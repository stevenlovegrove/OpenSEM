#pragma once

#include "serial_controller.h"

class Hp6624a {
public:
    Hp6624a(const std::string& port, size_t hpib_addr)
    {
        controller.connection_changed.connect([&,hpib_addr](EventConnection e){
            if(e.connected) {
                std::cout << "[connected] HPIB dongle" << std::endl;
                controller.send_pause(1500);
                command("++addr " + std::to_string(hpib_addr));
                command("++read_tmo_ms 500\n");

                idle();

                // Always startup with power off
                command("DCPON 0");
//                async::spawn([&](){
//                    auto version = controller.send_and_retrieve("++ver\n").get();
//                    std::cout << version << std::endl;
//                });

//                set_display("Connected");

            }else{
                std::cout << "[Disconnected] HPIB dongle" << std::endl;
            }
        });
        controller.connect(port,115200);

    }

    ~Hp6624a()
    {
        idle();
//        set_display("Disconnected");
    }

    bool is_connected() {
        return controller.is_connected();
    }

    void command(const std::string& cmd)
    {
//        std::cout << cmd << std::endl;
        controller.send(cmd + "\n");
        // Things go wrong if we send commands too quickly...
        controller.send_pause(20);
    }

    std::future<std::string> query(const std::string& cmd)
    {
        command(cmd);
        return controller.send_and_retrieve("++read\n");
    }

    void idle()
    {
        for(int i=1; i <= 4; ++i) {
            set_on_off(i, false);
        }
    }

    void set_display(std::string s)
    {
        std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){ return std::toupper(c); });
        command("DSP \"" + s + "\"");
    }

    void set_channel_val(const std::string& cmd, uint8_t channel, double val)
    {
        command(cmd + " " + std::to_string(channel) + " " + std::to_string(val));
    }

    double get_channel_val(const std::string& cmd, uint8_t channel)
    {
        auto q = query(cmd + "? " + std::to_string(channel));
        const double val = std::stod(q.get());
        return val;
    }

    void set_max_voltage(uint8_t channel, double voltage_volts)
    {
        set_channel_val("vset", channel, voltage_volts);
    }

    void set_max_current(uint8_t channel, double current_amps)
    {
        set_channel_val("iset", channel, current_amps);
    }

    double get_max_voltage(u_int8_t channel)
    {
        return get_channel_val("vset", channel);
    }

    double get_max_current(u_int8_t channel)
    {
        return get_channel_val("iset", channel);
    }

    double get_voltage(u_int8_t channel)
    {
        return get_channel_val("vout", channel);
    }

    double get_current(u_int8_t channel)
    {
        return get_channel_val("iout", channel);
    }

    void set_overcurrent_shutdown(uint8_t channel, bool enable)
    {
        set_channel_val("ocp", channel, enable ? 1.0 : 0.0);
    }

    void set_on_off(uint8_t channel, bool enable)
    {
        command("out " + std::to_string(channel) + " " + (enable ? "1" : "0") );
    }

private:

    SerialController controller;
};
