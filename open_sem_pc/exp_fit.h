#pragma once

#include <cmath>
#include <array>
#include <deque>

// Return best fit [a,c] of form y = c.e^(a.x)
// https://www.bragitoff.com/2015/09/c-program-for-exponential-fitting-least-squares/
std::array<double,2> exp_fit(const std::deque<std::array<double,2>>& data_points)
{
    using namespace std;

    const int n = data_points.size();
    double xsum=0,x2sum=0,ysum=0,xysum=0;

    for(const auto& p : data_points)
    {
        const double x = p[0];
        const double y = p[1];
        const double lny = log(y);
        xsum=xsum+x;                     //calculate sigma(xi)
        ysum=ysum+lny;                   //calculate sigma(yi)
        x2sum=x2sum+pow(x,2);            //calculate sigma(x^2i)
        xysum=xysum+x*lny;               //calculate sigma(xi*yi)
    }
    const double a = (n*xysum-xsum*ysum)/(n*x2sum-xsum*xsum);            //calculate slope(or the the power of exp)
    const double b = (x2sum*ysum-xsum*xysum)/(x2sum*n-xsum*xsum);        //calculate intercept
    const double c = exp(b);                                             //since b=ln(c)

    return {a,c};
}
