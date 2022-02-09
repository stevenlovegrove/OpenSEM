#pragma once

#include <serial/serial.h>
#include <sigslot/signal.hpp>
#include <async++.h>
#include <chrono>
#include <thread>
#include <future>
#include <iostream>
#include <deque>
#include <optional>

struct EventConnection
{
    bool connected;
};

struct EventUnpromptedMessage
{
    std::string data;
};

class SerialController
{
public:
    SerialController(size_t fixed_length = 0, const std::string& delimiter = "\n")
        : fixed_length(fixed_length), delimiter(delimiter), serial_baud(0)
    {
    }

    ~SerialController()
    {
        disconnect();
        if(serial_connection_task.valid()) {
            serial_connection_task.wait();
        }
    }

    void connect(const std::string& serial_filename, int baud)
    {
        if(serial_connection_task.valid()) {
            if(serial_filename == this->serial_filename) {
                // already connected
                return;
            }else{
                // connected to different device.
                // need to close this connection first.
                serial_connection_task.then([&](){
                    connect(serial_filename, baud);
                });
                if(!c.is_canceled()) {
                    c.cancel();
                }
                return;
            }
        }

        this->serial_filename = serial_filename;
        this->serial_baud = baud;

        serial_connection_task = async::spawn([&](){ serial_task_function(); } );
    }

    void disconnect()
    {
        c.cancel();
    }

    bool is_connected()
    {
        return serial_device.isOpen();
    }

    void send_pause(size_t wait_ms)
    {
        std::unique_lock<std::mutex> l(send_queue_lock);
        send_queue.emplace_back("", false);
        send_queue.back().wait_ms = wait_ms;
    }

    void send(const std::string& data)
    {
        std::unique_lock<std::mutex> l(send_queue_lock);
        send_queue.emplace_back(data, false);
    }

    std::future<std::string> send_and_retrieve(const std::string& data)
    {
        std::unique_lock<std::mutex> l(send_queue_lock);
        send_queue.emplace_back(data, true);
        return send_queue.back().promise.get_future();
    }

    sigslot::signal<EventConnection> connection_changed;
    sigslot::signal<EventUnpromptedMessage> on_unprompted_message;

private:
    struct Packet
    {
        Packet(const std::string& d, bool expect_response)
            : data(d), wait_ms(0), expect_response(expect_response) {}
        Packet(Packet&&) = default;

        std::promise<std::string> promise;
        std::string data;
        size_t wait_ms;
        bool expect_response;
    };

    void set_connection_status(bool connected)
    {
        if(this->connected != connected) {
            this->connected = connected;
            EventConnection e = {connected};
            connection_changed(e);
        }
        if(connected == false) {
            expecting_queue.clear();
        }
    }

    void serial_task_function()
    {
        c.reset();
        serial::Timeout to = serial::Timeout::simpleTimeout(10);
        serial_device.setTimeout(to);
        serial_device.setPort(serial_filename);
        serial_device.setBaudrate(serial_baud);

        while(true) {
            try {
                if(!serial_device.isOpen()) {
                    set_connection_status(false);

                    // Will throw on failure
                    serial_device.open();
                    set_connection_status(true);
                }

                if(serial_device.waitReadable()) {
                    const size_t read_len = fixed_length ? fixed_length : 65536;
                    const std::string r = serial_device.readline(read_len, delimiter);

                    if(r.size() > 0) {
                        if(expecting_queue.size()) {
                            Packet& packet = expecting_queue.front();
                            packet.promise.set_value(r);
                            expecting_queue.pop_front();
                        }else{
                            EventUnpromptedMessage mesg = {r};
                            on_unprompted_message(mesg);

                            if(!on_unprompted_message.slot_count()) {
                                unrequested_line_received(r);
                            }
                        }
                    }
                }

                // Trigger check that serial is actually still alive. Will throw if dead.
                serial_device.available();

                // we're the only ones popping front of queue, so no need to lock
                if(send_queue.size()) {
                    auto& packet = send_queue.front();
                    if(!packet.data.empty()) {
                        serial_device.write((uint8_t*)packet.data.data(), packet.data.size());
                        if(packet.expect_response) {
                            expecting_queue.emplace_back( std::move(packet) );
                        }
                    }
                    if(packet.wait_ms) {
                        std::this_thread::sleep_for(std::chrono::milliseconds(packet.wait_ms));
                    }
                    send_queue.pop_front();
                }
            } catch (const serial::IOException& e) {
                if( e.getErrorNumber() == 2) {
                    // no such port
                    // retry in a bit
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                }else if( e.getErrorNumber() == 6) {
                    // device not configured (probably got disconnected)
                    serial_device.close();
                }else if( e.getErrorNumber() == 16) {
                    // resource busy
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                } else {
                    std::cout << e.what() << std::endl;
                }
            }

            // Allow cancellation
            if(c.is_canceled()) {
                serial_device.close();
                set_connection_status(false);
                throw async::task_canceled();
            }
        }
    }

    void unrequested_line_received(const std::string& line)
    {
        std::cout << "[unrequested] " << line << " (";
        for(auto c : line) {
            std::cout << std::hex << (int) c;
        }
        std::cout << ")" << std::endl;
    }

    size_t fixed_length;
    const std::string delimiter;
    bool auto_reconnect;

    std::string serial_filename;
    uint32_t serial_baud;
    serial::Serial serial_device;
    async::task<void> serial_connection_task;
    async::cancellation_token c;
    bool connected = false;

    std::mutex send_queue_lock;
    std::deque<Packet> send_queue;
    std::deque<Packet> expecting_queue;
};

std::vector<std::string> AvailablePorts()
{
    const auto ports = serial::list_ports();

    // Check which ports are 'real' and have CTS set.
    std::vector<async::task<bool>> check_tasks;
    for(const auto& p : ports) {
        check_tasks.push_back(async::spawn([p](){
            serial::Serial s;
            try {
                s.setPort(p.port);
                s.open();
                return !s.getCTS();
            }  catch (const serial::SerialException& s) {
                std::cout << s.what() << std::endl;
            }
            return false;
        }));
    }

    std::vector<std::string> available_ports;
    for(int i=0; i < ports.size(); ++i) {
        if(check_tasks[i].get()) {
            available_ports.push_back(ports[i].port);
        }
    }
    return available_ports;
}
