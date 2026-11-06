#pragma once
#include <chrono>
#include <cmath>
#include <cstdint>
#include <optional>
namespace uamc_dashboard
{
using Clock = std::chrono::steady_clock;
inline bool fresh(bool received, Clock::time_point at, Clock::time_point now, double timeout)
{
  return received && std::chrono::duration<double>(now - at).count() <= timeout;
}
inline bool available(
  bool received, double value, Clock::time_point at, Clock::time_point now,
  double timeout)
{
  return fresh(received, at, now, timeout) && std::isfinite(value);
}
struct ImageLiveness
{
  bool seen = false, valid_stamp = false;
  int64_t stamp = 0;
  Clock::time_point received{}, advanced{};

  void receive(int32_t sec, uint32_t nanosec, Clock::time_point now)
  {
    seen = true;
    received = now;
    valid_stamp = sec >= 0 && nanosec < 1000000000U && (sec > 0 || nanosec > 0);
    if (!valid_stamp) {return;}
    const int64_t next = static_cast<int64_t>(sec) * 1000000000LL + nanosec;
    if (next > stamp) {advanced = now;}
    stamp = next;
  }

  bool live(Clock::time_point now, double timeout, int64_t ros_now) const
  {
    if (!seen || !valid_stamp || stamp <= 0 || ros_now <= 0 ||
      !fresh(true, received, now, timeout) || !fresh(true, advanced, now, timeout))
    {
      return false;
    }
    const double delta = static_cast<double>(ros_now - stamp) * 1e-9;
    return delta <= timeout && delta >= -0.25;
  }
};
struct GoalState
{
  bool pending = false, uncertain = false, owned = false;
  void request() {pending = true;}
  void timeout() {if(pending) {pending = false;uncertain = true;}}
  void response(bool accepted) {pending = false;uncertain = false;owned = accepted;}
  void result() {owned = false;uncertain = false;pending = false;}
  bool can_start(bool live, bool running) const
  {
    return live && !running && !pending && !uncertain && !owned;
  }
};
}
