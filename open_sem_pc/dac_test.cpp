#include <pangolin/display/display.h>
#include <pangolin/display/view.h>
#include <pangolin/handler/handler.h>
#include <pangolin/gl/gldraw.h>
#include <pangolin/plot/plotter.h>
#include <pangolin/display/widgets.h>
#include <pangolin/display/default_font.h>
#include <pangolin/utils/timer.h>
#include <pangolin/display/image_view.h>

#include <async++.h>
#include <chrono>
#include <thread>
#include <future>

struct RC
{
    RC(double v_0, double tau)
        : v_out(v_0), tau(tau)
    {
    }

    RC(double v_0, double resistance, double capacitance)
        : RC(v_0, resistance*capacitance)
    {
    }

    void step(double delta_t, double v_in)
    {
        v_out = charge_vout(delta_t, tau, v_in, v_out);
    }

    // derived
    static double charge_vout(double t, double tau, double vin, double vout_0)
    {
        return vin + (vout_0 - vin) * exp(-t/tau);
    }

//    // from wiki
//    static double charge_vout(double t, double tau, double vin)
//    {
//        return vin * (1- exp(-t/tau));
//    }

//    // from wiki
//    static double discharge_vout(double t, double tau, double v0)
//    {
//        return v0 * exp(-t/tau);
//    }

    double v_out;
    double tau;
};


struct DAC
{
    DAC(double rc_tau = 1.0)
        : rc(0.0, rc_tau)
    {

    }

    bool clock(double delta_t, double signal)
    {
        const bool s = signal > rc.v_out;
        rc.step(delta_t, s ? 1.0 : 0.0);
        return s;
    }

    RC rc;
};

double sawtooth(double t, double period)
{
    const double n = std::floor(t / period);
    const double frac = (t - n*period)/period;
    return frac;
}

double ppm(double t, double period, double duty_frac)
{
    return sawtooth(t, period) < duty_frac ? 1.0 : 0.0;
}

double sin(double t, double period)
{
    return 0.5 + std::sin(M_PI * t / period) / 2.0;
}

double some_func(double t)
{
    if(t < 1.0) return 0.1 + 0.5*sawtooth(t, 0.001);
    if(t < 2.0) return 0.1 + 0.2*ppm(t, 0.02, 0.2);
    if(t < 3.0) return 0.2 + 0.3*sin(t, 0.0001);
    return sin(t, 0.1);
}

int main( int /*argc*/, char** /*argv*/ )
{
    pangolin::CreateWindowAndBind("Main",640,480);
    glEnable(GL_DEPTH_TEST);

    constexpr double fps = 30;
    constexpr double h = 480;
    constexpr double w = 640;
    constexpr double delta_t = 1.0 / (100e6);
    constexpr double sim_time = delta_t * 1e6;


    const auto ui_width = pangolin::Attach::Pix(40* pangolin::default_font().MaxWidth());

    pangolin::Panel panel("ui");
    panel.SetBounds(0.0, 1.0, 0.0, ui_width);

    pangolin::DataLog dac_log;
    pangolin::Plotter plot_dac(&dac_log, 0.0, sim_time, 0, 1.0, 1.0/100e6, 1.0 / (1<<16));
    plot_dac.ClearSeries();
    plot_dac.AddSeries("$0", "$1", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "Signal");
    plot_dac.AddSeries("$0", "$2", pangolin::DrawingModePoints, pangolin::Colour::Unspecified(), "dac");
    plot_dac.AddSeries("$0", "$3", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "filter_perfect");
    plot_dac.AddSeries("$0", "$4", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "error");

    plot_dac.SetBounds(0.0, 1.0, ui_width, 1.0);
    pangolin::DisplayBase().AddDisplay(panel).AddDisplay(plot_dac);

    pangolin::Var<double> tau("ui.tau", 1e-6, 0, 1e-6);
    pangolin::Var<double> real_tau_diff("ui.real_tau_diff", 0.0, -1.0, 1.0);

//    if(true) {
//        const double vin = 0.5;
//        RC test(0.0, 1.0, 1.0);
//        for(int i=0; i < 1000; ++i) {
//            double alt = test.charge_vout(i*0.01, 1.0/1.0, vin);
//            dac_log.Log(test.v_out, alt);
//            test.step(0.01, vin);
//        }
//    }

//    if(false) {
//        const double vin = 0.0;
//        RC test(1.0, 1.0, 1.0);
//        for(int i=0; i < 1000; ++i) {
//            double alt = test.discharge_vout(i*0.01, 1.0/1.0, 1.0);
//            dac_log.Log(test.v_out, alt);
//            test.step(0.01, vin);
//        }
//    }

    auto sim = [&](){
        RC real_rc(0.0, real_tau_diff);
        DAC dac(tau);

        dac_log.Clear();

        for(double t=0; t < sim_time; t += delta_t)
        {
            double signal = 0.4 + 0.25 * sawtooth(t, 1.0 / (fps) );//some_func(t);

            const bool out = dac.clock(delta_t, signal);
            real_rc.step(delta_t, out ? 1.0 : 0.0);

            dac_log.Log( t, signal, out ? 1.0 : 0.0, dac.rc.v_out, std::abs(signal - dac.rc.v_out));
        }
    };

    while( !pangolin::ShouldQuit() )
    {
        if(pangolin::GuiVarHasChanged()) {
            sim();
        }

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        pangolin::FinishFrame();
    }

    return 0;
}
