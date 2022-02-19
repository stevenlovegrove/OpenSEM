#pragma once

#include <stdexcept>
#include <memory>
#include <cstdint>
#include <string>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <sigslot/signal.hpp>
#include <async++.h>
#include <ftd3xx.h>

#include <pangolin/image/managed_image.h>

std::string get_status(FT_STATUS status)
{
#define FTDI_CASE(x) case(x): return #x
    switch (status) {
        FTDI_CASE(FT_OK);
        FTDI_CASE(FT_INVALID_HANDLE);
        FTDI_CASE(FT_DEVICE_NOT_FOUND);
        FTDI_CASE(FT_DEVICE_NOT_OPENED);
        FTDI_CASE(FT_IO_ERROR);
        FTDI_CASE(FT_INSUFFICIENT_RESOURCES);
        FTDI_CASE(FT_INVALID_PARAMETER);
        FTDI_CASE(FT_INVALID_BAUD_RATE);
        FTDI_CASE(FT_DEVICE_NOT_OPENED_FOR_ERASE);
        FTDI_CASE(FT_DEVICE_NOT_OPENED_FOR_WRITE);
        FTDI_CASE(FT_FAILED_TO_WRITE_DEVICE);
        FTDI_CASE(FT_EEPROM_READ_FAILED);
        FTDI_CASE(FT_EEPROM_WRITE_FAILED);
        FTDI_CASE(FT_EEPROM_ERASE_FAILED);
        FTDI_CASE(FT_EEPROM_NOT_PRESENT);
        FTDI_CASE(FT_EEPROM_NOT_PROGRAMMED);
        FTDI_CASE(FT_INVALID_ARGS);
        FTDI_CASE(FT_NOT_SUPPORTED);
        FTDI_CASE(FT_NO_MORE_ITEMS);
        FTDI_CASE(FT_TIMEOUT/*19*/);
        FTDI_CASE(FT_OPERATION_ABORTED);
        FTDI_CASE(FT_RESERVED_PIPE);
        FTDI_CASE(FT_INVALID_CONTROL_REQUEST_DIRECTION);
        FTDI_CASE(FT_INVALID_CONTROL_REQUEST_TYPE);
        FTDI_CASE(FT_IO_PENDING);
        FTDI_CASE(FT_IO_INCOMPLETE);
        FTDI_CASE(FT_HANDLE_EOF);
        FTDI_CASE(FT_BUSY);
        FTDI_CASE(FT_NO_SYSTEM_RESOURCES);
        FTDI_CASE(FT_DEVICE_LIST_NOT_READY);
        FTDI_CASE(FT_DEVICE_NOT_CONNECTED);
        FTDI_CASE(FT_INCORRECT_DEVICE_PATH);
        FTDI_CASE(FT_OTHER_ERROR);
    default: return "";
    }
#undef FTDI_CASE
}

class FtdiConnection
{
public:
    FtdiConnection()
        : handle(nullptr), timeout_ms(1000)
    {
    }

    ~FtdiConnection()
    {
        Disconnect();
    }

    FtdiConnection(const FtdiConnection&) = delete;

    bool connect()
    {
        if(!handle) {
            // device seems to get stuck if we open it, read from it once, then close it.
            // If we read at least twice with a small pause between the reads, it does fine
            // when we reopen it next time around. Otherwise, we seem to need to unplug / replug.
            // FT_ResetDevicePort / Cycle / flush etc - none of these seem to help
            FT_STATUS s = FT_Create(0, FT_OPEN_BY_INDEX, &handle);
            return FT_SUCCESS(s);
        }
        return true;
    }

    void Disconnect()
    {
        if(handle) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            FT_Close(handle);
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            handle = nullptr;
        }
    }

    size_t read(uint8_t* buffer, size_t max_read)
    {
        uint32_t read;
        FT_STATUS status = FT_ReadPipeEx(handle, 0 , buffer, max_read, &read, timeout_ms);

        if(FT_FAILED(status)) {
            switch (status) {
            case FT_INVALID_HANDLE:
                [[fallthrough]];
            case FT_DEVICE_NOT_FOUND:
                [[fallthrough]];
            case FT_DEVICE_NOT_OPENED:
                Disconnect();
            default: break;
            }
        }

        return read;
    }

    bool connected()
    {
        return handle;
    }

    FT_HANDLE handle;
    size_t timeout_ms;
};

class ScanController
{
public:

    ScanController()
        : image(512,512), mbps(0)
    {
        connect();
    }

    ~ScanController()
    {
        disconnect();
    }

    void connect()
    {
        if(!connection_task.valid()) {
            c.reset();
            connection_task = async::spawn(
                std::bind(&ScanController::connection_loop, this)
            );
        }
    }

    void disconnect()
    {
        if(connection_task.valid()) {
            c.cancel();
            connection_task.wait();
        }
    }

    void connection_loop()
    {
        FtdiConnection ftdi;
        const int32_t max_read_bytes = 2*10*image.w;

        auto t_connect = std::chrono::steady_clock::now();
        size_t total_bytes = 0;

        while(!c.is_canceled()) {
            // Establish connection
            while(!ftdi.connected()) {
                if(!ftdi.connect()) {
                    async::interruption_point(c);
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                }
            }

            // Fill up an image worth of data
            int32_t bytes_for_image = image.SizeBytes();
            uint8_t* p = (uint8_t*)image.ptr;

            while(ftdi.connected() && bytes_for_image > 0) {
                async::interruption_point(c);
                const size_t bytes_read = ftdi.read(p, std::min(bytes_for_image, max_read_bytes) );
                if(bytes_read) {
                    bytes_for_image -= bytes_read;
                    p += bytes_read;
                    total_bytes += bytes_read;

                    auto t_now = std::chrono::steady_clock::now();
                    double t_diff = std::chrono::duration_cast<std::chrono::seconds>(t_now - t_connect).count();
                    mbps = total_bytes / t_diff / 1024 / 1024;
                }else{
                    std::cout << "FTDI Timeout (or something)." << std::endl;
                }
            }
        }
    }

    pangolin::Image<uint16_t> get_image()
    {
        return image;
    }

//private:
    async::task<void> connection_task;
    async::cancellation_token c;

    pangolin::ManagedImage<uint16_t> image;
    double mbps;
};
