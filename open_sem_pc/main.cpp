#include <pangolin/display/display.h>
#include <pangolin/display/view.h>
#include <pangolin/handler/handler.h>
#include <pangolin/gl/gldraw.h>
#include <pangolin/plot/plotter.h>
#include <pangolin/display/widgets.h>
#include <pangolin/display/default_font.h>

#include <serial/serial.h>
#include <async++.h>
#include <chrono>
#include <thread>
#include <future>

// TODO:
// * survive serial port opens / closes
// * show serial port status
// * have time on x-axis for plot
// * add events as markers on plot
// * switch to instance voltage setting. Reset voltage slider during idle etc.
// * eta based on exponential fit of recent data
// * create re-viewable log of events / pressure / voltage

int main( int /*argc*/, char** /*argv*/ )
{
    const char* sem_vac = "/dev/cu.usbmodem1301";
    const char* sem_hv = "/dev/cu.usbserial-120";

    serial::Serial serial_vac;
    serial::Serial serial_hv;
    async::cancellation_token stop_all;

    serial_vac.setPort(sem_vac);
    serial_hv.setPort(sem_hv);

    pangolin::DataLog pressure_log;
    float current_pressure;

    auto pressure_task = async::spawn([&](){
        while(true) {
            try {
                std::cout << "llop" << std::endl;
                if(!serial_vac.isOpen()) {
                    serial_vac.open();
                }
                if(serial_vac.waitReadable()) {
                    std::string r = serial_vac.readline();
                    if(r.size() > 0) {
                        if(r[0] == 'P' && r.size() == 6) {
                            const float f = *((float*)&(r[1]));
                            pressure_log.Log(f);
                            current_pressure = f;
                        }
                    }
                }
            } catch (std::exception& e) {
                std::cout << e.what() << std::endl;
            }
            async::interruption_point(stop_all);
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    });

    pangolin::CreateWindowAndBind("Main",640,480);
    glEnable(GL_DEPTH_TEST);

    const int UI_WIDTH = 40* pangolin::default_font().MaxWidth();

    pangolin::CreatePanel("ui")
      .SetBounds(0.0, 1.0, 0.0, pangolin::Attach::Pix(UI_WIDTH));

    pangolin::Plotter plot_pressure(&pressure_log, 0, 600, 0, 850, 60, 100);
    plot_pressure.SetBounds(0.0, 1.0, pangolin::Attach::Pix(UI_WIDTH), 1.0);
    plot_pressure.AddMarker(pangolin::Marker::Direction::Horizontal, 0.8);
    plot_pressure.AddMarker(pangolin::Marker::Direction::Horizontal, 1e-4);

    pangolin::DisplayBase().AddDisplay(plot_pressure);

    auto ser_write  =[&](serial::Serial& port, const char* packet)
    {
        try {
            if(!port.isOpen()) {
                port.open();
            }
            if(port.write((uint8_t*)packet, 2) != 2) {
                std::cerr << "Didn't write all of packet" << std::endl;
            }
        }  catch (std::exception& e) {
            // problem with port
            port.close();
        }
    };

    auto write_hv = [&](const char* packet){ser_write(serial_hv, packet);};
    auto write_vac = [&](const char* packet){ser_write(serial_vac, packet);};

    auto vac_idle    = [&](){write_vac("==");};
    auto vac_rough   = [&](){write_vac("<<");};
    auto vac_turbo   = [&](){write_vac("<+");};
    auto vac_vent    = [&](){write_vac(">+");};
    auto vac_set_atm = [&](){write_vac("CA");};

    auto hv_idle = [&](){write_hv("..");};
    auto hv_on   = [&](){write_hv("!!");};
    auto hv_set_voltage = [&](float voltage) {
        if(0 <= voltage && voltage <= 30000) {
            const float val_f = 256.0 * voltage / 30000.0;
            char packet[2];
            packet[0] = 'V';
            packet[1] = static_cast<char>(val_f);
            write_hv(packet);
        }
    };

    auto idle_all = [&](){
        vac_idle();
        hv_idle();
    };

    pangolin::Var<bool> connected_hv("ui.connected_HV", false, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);
    pangolin::Var<bool> connected_vac("ui.connected_VAC", false, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);

    pangolin::Var<std::string>("ui.Vacuum","", pangolin::META_FLAG_READONLY);

    pangolin::Var<float>::Attach("ui.Pressure", current_pressure, 0.0, 800);
    pangolin::Var<std::function<void(void)>>("ui.Idle", vac_idle);
    pangolin::Var<std::function<void(void)>>("ui.Rough", vac_rough);
    pangolin::Var<std::function<void(void)>>("ui.Turbo", vac_turbo);
    pangolin::Var<std::function<void(void)>>("ui.Vent",  vac_vent);
    pangolin::Var<std::function<void(void)>>("ui.Set_ATM", vac_set_atm);

    pangolin::Var<std::string>("ui.Acc Voltage","", pangolin::META_FLAG_READONLY);
    pangolin::Var<std::function<void(void)>>("ui.HT_off", hv_idle);
    pangolin::Var<std::function<void(void)>>("ui.HT_on", hv_on);
    pangolin::Var<float> ui_voltage("ui.HT_Voltage", 0.0, 0.0, 1000.0);
    pangolin::Var<std::function<void(void)>>("ui.Set_Voltage", [&](){
        hv_set_voltage(ui_voltage);
    });

    pangolin::RegisterKeyPressCallback(' ', idle_all);

    while( !pangolin::ShouldQuit() )
    {
        connected_hv = serial_hv.isOpen();
        connected_vac = serial_vac.isOpen();

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        pangolin::FinishFrame();
    }

    stop_all.cancel();
    pressure_task.wait();

    return 0;
}
