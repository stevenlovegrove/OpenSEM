#pragma once

#include <functional>
#include <thread>
#include <chrono>

template<typename... FArgs>
class RateLimitedFunctionCall
{
public:
    RateLimitedFunctionCall(std::function<void(FArgs...)> func, double min_delay_s)
        : f(func), min_delay_s(min_delay_s)
    {
    }

    template <typename... Args>
    void operator()(Args&&... args)
    {
        const auto now = std::chrono::system_clock::now();
        std::chrono::duration<double> diff = now - last_call;
        if(diff.count() > min_delay_s) {
            f(std::forward<Args>(args)...);
            last_call = now;
        }
    }

    std::function<void(FArgs...)> f;
    double min_delay_s;
    std::chrono::time_point<std::chrono::system_clock> last_call;
};
