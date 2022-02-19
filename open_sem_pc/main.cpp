#include <pangolin/display/display.h>
#include <pangolin/display/view.h>
#include <pangolin/handler/handler.h>
#include <pangolin/gl/gldraw.h>
#include <pangolin/plot/plotter.h>
#include <pangolin/display/widgets.h>
#include <pangolin/display/default_font.h>
#include <pangolin/utils/timer.h>
#include <pangolin/display/image_view.h>

#include <serial/serial.h>
#include <async++.h>
#include <chrono>
#include <thread>
#include <future>

#include "rate_limited_function_call.h"
#include "serial_controller.h"
#include "Hp6624a.h"
#include "KilovoltsHR30.h"
#include "vacuum_controller.h"
#include "exp_fit.h"
#include "scan_controller.h"

// TODO:
// * create re-viewable log of events / pressure / voltage

std::array<double,2> datalog_exp_fit(const pangolin::DataLog& log, size_t last_k_samples)
{
    assert(log.LastBlock()->Dimensions() == 2);
    const size_t n = log.Samples();

    std::deque<std::array<double,2>> data;
    for(size_t i=0; i < std::min(n, last_k_samples); ++i)
    {
        const float* vec = log.Sample(n-1-i);
        data.push_back({vec[0], vec[1]});
    }

    return exp_fit(data);
}

void test()
{
    pangolin::CreateWindowAndBind("Main",640,480);
    glEnable(GL_DEPTH_TEST);

    pangolin::ImageView view;
    pangolin::DisplayBase().AddDisplay(view);

//    auto image = pangolin::LoadImage("/Users/stevenlovegrove/Downloads/test.jpeg");
    pangolin::ManagedImage<uint16_t> image(512,512);

    while( !pangolin::ShouldQuit() )
    {
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        view.SetImage(image);
        pangolin::FinishFrame();
    }
}

int main( int /*argc*/, char** /*argv*/ )
{
//    auto ports = AvailablePorts();
//    for(const auto& p : ports) {
//        std::cout << p << std::endl;
//    }

//    test();
//    return 0;

    const char* sem_hp = "/dev/cu.usbserial-110";
    const char* sem_vac = "/dev/cu.usbmodem1301";
    const char* sem_hv = "/dev/cu.usbserial-120";


    Hp6624a hp_supply(sem_hp, 7);
    KilovoltsHR30 hv_supply(sem_hv);
    VacuumController vacuum(sem_vac);
    ScanController scanner;

    pangolin::CreateWindowAndBind("Main",640,480);
    glEnable(GL_DEPTH_TEST);

    const auto ui_width = pangolin::Attach::Pix(40* pangolin::default_font().MaxWidth());

    pangolin::Panel panel("ui");
    panel.SetBounds(0.0, 1.0, 0.0, ui_width);

    pangolin::DataLog pressure_log;
    pangolin::DataLog pressure_fit;
    pangolin::View container;
    pangolin::ImageView image_view;
    pangolin::Plotter plot_pressure(&pressure_log, 0, 600, 0, 800, 10, 1e-4);
    plot_pressure.ClearSeries();
    plot_pressure.AddSeries("$0", "$1");
    plot_pressure.AddMarker(pangolin::Marker::Direction::Horizontal, 0.8);
    plot_pressure.AddMarker(pangolin::Marker::Direction::Horizontal, 1e-4);
    plot_pressure.AddSeries("$0", "$1", pangolin::DrawingModeDashed, pangolin::Colour::Unspecified(), "fit", &pressure_fit);

    double refresh_fit = false;
    std::array<double,2> exp_fit = {0.0, 0.0};

    // Setup logging of pressure output
    const float program_start = pangolin::TimeNow_s();
    vacuum.on_pressure_reading_torr.connect([&](double pressure_torr){
        const float t = pangolin::TimeNow_s() - program_start;
        pressure_log.Log(t, pressure_torr);
        exp_fit = datalog_exp_fit(pressure_log, 30);
        std::cout << exp_fit[0] << std::endl;
        std::cout << exp_fit[1] << std::endl;
        refresh_fit = true;
    });

    container.SetLayout(pangolin::LayoutEqual)
            .SetBounds(0.0, 1.0, ui_width, 1.0)
            .SetHandler(&pangolin::StaticHandler)
            .AddDisplay(image_view)
            .AddDisplay(plot_pressure);


    pangolin::DisplayBase().AddDisplay(panel).AddDisplay(container);

    auto idle_all = [&](){
        hv_supply.idle();
        hp_supply.idle();
        vacuum.idle();
    };

    pangolin::Var<bool> connected_hv("ui.Connected_High_Voltage", false, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);
    pangolin::Var<bool> connected_hp("ui.Connected_Coil_Power", false, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);
    pangolin::Var<bool> connected_vac("ui.Connected_Vacuum", false, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);


    pangolin::Var<double> current_pressure("ui.Pressure", 0.0, pangolin::META_FLAG_READONLY | pangolin::META_FLAG_TOGGLE);
    pangolin::Var<std::function<void(void)>>("ui.Idle", [&](){vacuum.idle();});
    pangolin::Var<std::function<void(void)>>("ui.Rough", [&](){vacuum.rough();});
    pangolin::Var<std::function<void(void)>>("ui.Turbo", [&](){vacuum.turbo();});
    pangolin::Var<std::function<void(void)>>("ui.Vent",  [&](){vacuum.vent();});
    pangolin::Var<std::function<void(void)>>("ui.Set_ATM", [&](){vacuum.calibrate_atmospheric();});


    pangolin::Var<std::string>("ui.Vacuum","", pangolin::META_FLAG_READONLY);


    pangolin::Var<bool> enable_hv("ui.Enable_HV", false, true);
    pangolin::Var<std::string>("ui.Acceleration","", pangolin::META_FLAG_READONLY);

    pangolin::Var<double> coil_condensor1("ui.condensor1_voltage", 0.0, 0.0, 4.0);
    pangolin::Var<double> coil_condensor2("ui.condensor2_voltage", 0.0, 0.0, 4.0);
    pangolin::Var<double> coil_objective("ui.objective_voltage",  0.0, 0.0, 4.0);
    pangolin::Var<double> coil_max_current("ui.coil_current",  0.0, 0.0, 2.0);
    pangolin::Var<bool> enable_amp("ui.Enable_Amp", false, true);
    pangolin::Var<bool> enable_coils("ui.Enable_Coils", false, true);
    pangolin::Var<std::string>("ui.Coils","", pangolin::META_FLAG_READONLY);
    pangolin::Var<double>::Attach("ui.ftdi_MBPS", scanner.mbps);

    RateLimitedFunctionCall<> update_supply_vars(
        [&](){
            hp_supply.set_max_voltage(1, coil_condensor1);
            hp_supply.set_max_voltage(2, coil_condensor2);
            hp_supply.set_max_voltage(3, coil_objective);
            for(int i=1; i <= 3; ++i) {
                hp_supply.set_max_current(i, coil_max_current);
            }
        }, 0.1
    );


    pangolin::RegisterKeyPressCallback(pangolin::PANGO_SPECIAL + pangolin::PANGO_KEY_TAB, idle_all);

    while( !pangolin::ShouldQuit() )
    {
        // Connection status
        connected_hv = hv_supply.is_connected();
        connected_hp = hp_supply.is_connected();
        connected_vac = vacuum.is_connected();

        // High-voltage supply logic
        if(hv_supply.is_connected()) {
            if(hv_supply.is_high_voltage_on() != enable_hv) {
                hv_supply.set_on_off(enable_hv);
            }
        }else{
            enable_hv = false;
        }

        // HP Power supply logic
        if(hp_supply.is_connected())
        {
            if(coil_condensor1.GuiChanged() || coil_condensor2.GuiChanged() || coil_objective.GuiChanged() || coil_max_current.GuiChanged()) {
                update_supply_vars();
            }
            if(enable_amp.GuiChanged()) {
                if(enable_amp) {
                    hp_supply.set_max_voltage(4, 32);
                    hp_supply.set_max_current(4, 0.5);
                }
                hp_supply.set_on_off(4, enable_amp);
            }
            if(enable_coils.GuiChanged()) {
                if(enable_coils) {
                    update_supply_vars();
                }
                hp_supply.set_on_off(1, enable_coils);
                hp_supply.set_on_off(2, enable_coils);
                hp_supply.set_on_off(3, enable_coils);
            }
        }else{
            enable_amp = false;
            enable_coils = false;
        }

        // Vacuum controller logic.
        current_pressure = vacuum.pressure();

        if(refresh_fit) {
            refresh_fit = false;
            pressure_fit.Clear();
            const double now = pangolin::TimeNow_s() - program_start;
            for(double time = now-30.0; time < now+180; time += 0.5)
            {
                pressure_fit.Log(time, exp_fit[1] * exp(exp_fit[0] * time));
            }
        }

        image_view.SetImage(scanner.image);

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        pangolin::FinishFrame();
    }

    idle_all();

    return 0;
}
