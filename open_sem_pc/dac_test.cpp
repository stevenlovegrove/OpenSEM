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
        : tau(tau), v_out(v_0)
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

    double tau;
    double v_out;
};


struct DAC
{
    DAC(size_t n)
        : n(n)
    {

    }

    bool clock(double signal)
    {
        current_avg = avg();
        const bool out = signal > current_avg;
        dac_hist.push_back(out);
        if( dac_hist.size() > n ) dac_hist.pop_front();
        return out;
    }

    double avg()
    {
        double sum = 0;
        double max = 0;

        const size_t els = dac_hist.size();
        for(int i=0; i < els; ++i) {
            double w = double(els-i) / els;
            double val = dac_hist[els-i-1] * w;
            max += w;
            sum += val;
        }
//        for(bool b : dac_hist) {
//            if(b) ++sum;
//        }
        return sum / max;
    }

    double current_avg;
    size_t n;
    std::deque<bool> dac_hist;
};

int main( int /*argc*/, char** /*argv*/ )
{
    pangolin::CreateWindowAndBind("Main",640,480);
    glEnable(GL_DEPTH_TEST);

    const size_t n = 1 << 12;
    std::cout << n << std::endl;

    const auto ui_width = pangolin::Attach::Pix(40* pangolin::default_font().MaxWidth());

    pangolin::Panel panel("ui");
    panel.SetBounds(0.0, 1.0, 0.0, ui_width);

    pangolin::DataLog dac_log;
    pangolin::Plotter plot_dac(&dac_log, 0, 600, 0, 1.0, 1.0, 1.0);

    plot_dac.SetBounds(0.0, 1.0, ui_width, 1.0);
    pangolin::DisplayBase().AddDisplay(panel).AddDisplay(plot_dac);

    pangolin::Var<double> signal("ui.level", 0, 0, 1.0);

    DAC dac(n);

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


    while( !pangolin::ShouldQuit() )
    {
        const bool out = dac.clock(signal);

//        dac_log.Log( signal, out ? 1.0 : 0.0, dac.current_avg);

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        pangolin::FinishFrame();
    }

    return 0;
}
