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

struct RCmulti
{
    RCmulti(double v_0, std::vector<double> resistances, double capacitance)
        : v_out(v_0)
    {
        for(double r : resistances) {
            inv_taus.push_back(1.0 / (r*capacitance));
        }
    }

    void step(double delta_t, const std::vector<double>& v_ins)
    {
        v_out += delta_v(delta_t, v_ins);
    }

    // vin is nan for high impedance
    double delta_v(double delta_t, const std::vector<double>& v_ins)
    {
        if(v_ins.size() != inv_taus.size())
            throw std::invalid_argument("v_ins wrong size.");

        double dv = 0;
        for(size_t i=0; i < inv_taus.size(); ++i) {
            if(std::isfinite(v_ins[i])) {
                dv += delta_t * inv_taus[i] * (v_ins[i] - v_out);
            }
        }
        return dv;
    }

    double v_out;
    std::vector<double> inv_taus;
};

size_t npow(size_t value, size_t exponent)
{
    if(exponent == 0) {
        return 1;
    }else if(exponent == 1) {
        return value;
    }else{
        return value * npow(value, exponent - 1);
    }
}

struct MultiDimLoop
{
    MultiDimLoop(size_t dims, size_t max_it)
        : dims(dims), max_its(dims, max_it), counter(dims), overflow(false)
    {
    }

    operator bool() const
    {
        return !overflow;
    }

    void operator++()
    {
        counter[0]++;
        for(int i=0; i < dims; ++i) {
            if(counter[i] >= max_its[i]) {
                counter[i] = 0;
                if( i == dims-1) {
                    overflow = true;
                    return;
                }else{
                    counter[i+1]++;
                }
            }else{
                return;
            }
        }
    }

    size_t n() const
    {
        size_t num_its=0;
        for(size_t i : max_its) num_its += i;
        return num_its;
    }


    size_t i() const
    {
        size_t flat = 0;
        size_t base = 1;
        for(size_t i=0; i < dims; ++i) {
            flat += base * counter[i];
            base *= max_its[i];
        }
        return flat;
    }

    const std::vector<size_t>& loop() const
    {
        return counter;
    }

    size_t operator [](size_t i)
    {
        return counter[i];
    }

private:
    const size_t dims;
    const std::vector<size_t> max_its;
    std::vector<size_t> counter;
    bool overflow;
};

struct DAC
{
    DAC(std::vector<double> resistances, double capacitance)
        : rc(0.0, resistances, capacitance), output(resistances.size(), 0.0)
    {
        const size_t num_bits = resistances.size();

        for(MultiDimLoop it(num_bits, 3); it; ++it)
        {
            options.push_back(option_to_signal(it.loop()));
        }
    }

    static std::vector<double> option_to_signal(const std::vector<size_t>& opt)
    {
        std::vector<double> ret;
        for(size_t o: opt) {
            const double val = o == 0 ? 0 : (o==1.0 ? 1.0 : std::numeric_limits<double>::quiet_NaN());
            ret.push_back( val );
        }
        return ret;
    }

    void clock(double delta_t, double signal)
    {
        size_t best_opt = 0;
        double best_diff = std::numeric_limits<double>::max();

        for(size_t i=0; i < options.size(); ++i) {
            const double delta_v = rc.delta_v(delta_t, options[i]);
            const double abs_diff = std::abs(rc.v_out + delta_v - signal);
            if(abs_diff < best_diff) {
                best_opt = i;
                best_diff = abs_diff;
            }
        }

        output = options[best_opt];

        rc.step(delta_t, output);
    }

    RCmulti rc;
    std::vector<double> output;

    std::vector<std::vector<double>> options;
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

    // 3840 x 2160
    constexpr double fps = 30;
    constexpr double h = 480;
    constexpr double w = 640;
    constexpr double delta_t = 1.0 / (100e6);
    constexpr double sim_time = delta_t * 1e5;


    const auto ui_width = pangolin::Attach::Pix(40* pangolin::default_font().MaxWidth());

    pangolin::Panel panel("ui");
    panel.SetBounds(0.0, 1.0, 0.0, ui_width);

    pangolin::DataLog dac_log;
    pangolin::Plotter plot_dac(&dac_log, 0.0, sim_time, 0, 1.0, 1.0/100e6, 1.0 / (1<<16));
    plot_dac.ClearSeries();
    plot_dac.AddSeries("$0", "$1", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "Signal");
    plot_dac.AddSeries("$0", "$2", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "filter_perfect");
    plot_dac.AddSeries("$0", "$3", pangolin::DrawingModeLine, pangolin::Colour::Unspecified(), "error");
    plot_dac.AddSeries("$0", "$4", pangolin::DrawingModePoints, pangolin::Colour::Unspecified(), "dac0");
    plot_dac.AddSeries("$0", "$5", pangolin::DrawingModePoints, pangolin::Colour::Unspecified(), "dac1");
    plot_dac.AddSeries("$0", "$6", pangolin::DrawingModePoints, pangolin::Colour::Unspecified(), "dac2");

    plot_dac.SetBounds(0.0, 1.0, ui_width, 1.0);
    pangolin::DisplayBase().AddDisplay(panel).AddDisplay(plot_dac);

    std::vector<double> resistances = {1000, 2000, 4000};
    double capacitance = 1e-7;

    pangolin::Var<double>::Attach("ui.R0", resistances[0], 500, 1e4);
    pangolin::Var<double>::Attach("ui.R1", resistances[1], 500, 1e4);
    pangolin::Var<double>::Attach("ui.R2", resistances[2], 500, 1e4);
    pangolin::Var<double>::Attach("ui.C", capacitance, 1e-10, 1e-7);

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
        DAC dac(resistances, capacitance);

        dac_log.Clear();

        for(double t=0; t < sim_time; t += delta_t)
        {
//            const double signal = 0.4 + 0.25 * sawtooth(t, 1.0 / (h*fps) );
            const double signal = sawtooth(t, 1.0 / (h*fps) );
//            const double signal = sqrt(2)/2.0;
//            const double signal = 0.4 + 0.25 * some_func(t);
            dac.clock(delta_t, signal);

            dac_log.Log( t, signal, dac.rc.v_out, std::abs(signal - dac.rc.v_out), dac.output[0], dac.output[1], dac.output[2]);
        }
    };

//    auto sim = [&](){
//        RCmulti rc1(0.0, {1.0,2.0}, 1e-6);
//        RCmulti rc2(0.0, {1.0,2.0}, 1e-6);
//        RCmulti rc3(0.0, {1.0,2.0}, 1e-6);

//        dac_log.Clear();

//        double t=0;
//        for(; t < sim_time/2.0; t += delta_t)
//        {
//            rc1.step(delta_t, {1.0, std::numeric_limits<double>::quiet_NaN()});
//            rc2.step(delta_t, {std::numeric_limits<double>::quiet_NaN(), 1.0});
//            rc3.step(delta_t, {1.0, 1.0});
//            dac_log.Log( t, rc1.v_out , rc2.v_out , rc3.v_out);
//        }

//        for(; t < sim_time; t += delta_t)
//        {
//            rc1.step(delta_t, {0.0, std::numeric_limits<double>::quiet_NaN()});
//            rc2.step(delta_t, {std::numeric_limits<double>::quiet_NaN(), 0.0});
//            rc3.step(delta_t, {0.0, 0.0});
//            dac_log.Log( t, rc1.v_out , rc2.v_out , rc3.v_out);
//        }
//    };

    sim();

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
