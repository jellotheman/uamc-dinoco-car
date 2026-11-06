#pragma once
#include "uamc_dashboard/dashboard_state.hpp"
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <uamc_interfaces/msg/safety_status.hpp>
#include <uamc_interfaces/msg/obstacle.hpp>
#include <uamc_interfaces/msg/vehicle_status.hpp>
#include <uamc_interfaces/action/drive_round1.hpp>
#include <ackermann_msgs/msg/ackermann_drive_stamped.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_srvs/srv/set_bool.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <QString>
#include <atomic>
#include <chrono>
#include <cmath>
#include <mutex>
#include <thread>

namespace uamc_dashboard
{

using Status = uamc_interfaces::msg::SafetyStatus;
using Drive = ackermann_msgs::msg::AckermannDriveStamped;
using Obstacle = uamc_interfaces::msg::Obstacle;
using Vehicle = uamc_interfaces::msg::VehicleStatus;
using Odom = nav_msgs::msg::Odometry;
using Action = uamc_interfaces::action::DriveRound1;
using Goal = rclcpp_action::ClientGoalHandle<Action>;
struct Sample
{
  double value = 0; Clock::time_point when{}; int64_t stamp = 0; bool present = false;
  void set(double v, const builtin_interfaces::msg::Time & time)
  {
    value = v; when = Clock::now(); stamp = rclcpp::Time(time).nanoseconds(); present = true;
  }
  QString text(double timeout, const char *unit) const
  {
    if (!available(present, value, when, Clock::now(), timeout)) {return "unavailable";}
    return QString::number(value, 'f', 2) + " " + unit;
  }
};
class Client {
public:
  explicit Client(bool sim)
  : simulation(sim)
  {
    rclcpp::NodeOptions options;
    options.parameter_overrides({rclcpp::Parameter("use_sim_time", sim)});
    node = std::make_shared<rclcpp::Node>("uamc_dashboard", options);
    status_sub = node->create_subscription<Status>(
      "/safety/status", rclcpp::QoS(10).reliable().durability_volatile(),
      [this](Status::SharedPtr m) {
        bool retry_disarm = false;
        {
          std::lock_guard<std::mutex> l(mu);
          if (status_seen && status.mode != m->mode) {
            req_speed.present = false;
            req_steer.present = false;
          }
          status = *m;
          status_seen = true;
          status_at = Clock::now();
          if (reconcile_disarm && m->armed && !disarm_pending &&
              age(last_reconcile) > 1.0) {
            retry_disarm = true;
            last_reconcile = Clock::now();
          }
        }
        if (retry_disarm) {arm(false);}
      });
    auto_sub = node->create_subscription<Drive>("/drive/requested", 10, [this](Drive::SharedPtr m){
          requested(m, false);
      });
    manual_sub = node->create_subscription<Drive>("/drive/manual", 10, [this](Drive::SharedPtr m){
          requested(m, true);
      });
    command_sub = node->create_subscription<Drive>("/drive/command", 10, [this](Drive::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); cmd_speed.set(m->drive.speed, m->header.stamp);
          cmd_steer.set(m->drive.steering_angle, m->header.stamp);
      });
    wheel_sub = node->create_subscription<Odom>("/odometry/wheel", rclcpp::SensorDataQoS(), [this](Odom::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); speed.set(m->twist.twist.linear.x, m->header.stamp);
      });
    obstacle_sub = node->create_subscription<Obstacle>("/perception/obstacle", 10,
        [this](Obstacle::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); obstacle = *m; obstacle_at = Clock::now();
          obstacle_seen = true; clearance.set(m->clearance_m, m->header.stamp);
      });
    vehicle_sub = node->create_subscription<Vehicle>("/vehicle/status", 10,
        [this](Vehicle::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); vehicle = *m; vehicle_at = Clock::now();
          vehicle_seen = true;
      });
    raw_sub = node->create_subscription<sensor_msgs::msg::Image>("/camera/image_raw",
        rclcpp::SensorDataQoS(), [this](sensor_msgs::msg::Image::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); raw_image.receive(
            m->header.stamp.sec, m->header.stamp.nanosec, Clock::now());
      });
    debug_sub = node->create_subscription<sensor_msgs::msg::Image>("/perception/lane/debug_image",
        rclcpp::SensorDataQoS(), [this](sensor_msgs::msg::Image::SharedPtr m){
          std::lock_guard<std::mutex> l(mu); debug_image.receive(
            m->header.stamp.sec, m->header.stamp.nanosec, Clock::now());
      });
    arm_client = node->create_client<std_srvs::srv::SetBool>("/safety/arm");
    reset_client = node->create_client<std_srvs::srv::Trigger>("/safety/reset");
    action = rclcpp_action::create_client<Action>(node, "/round1/run");
    executor.add_node(node); thread = std::thread([this]{
          while(!stopping) {
            executor.spin_some(); std::this_thread::sleep_for(std::chrono::milliseconds(20));
          }
      });
    clock_at = Clock::now();
  }
  ~Client()
  {
    stopping = true; executor.cancel(); if(thread.joinable()) {
      thread.join();
    }
    executor.remove_node(node);
  }
  void requested(Drive::SharedPtr m, bool manual)
  {
    std::lock_guard<std::mutex> l(mu); if(!status_seen || (status.mode == "manual") != manual) {
      return;
    }
    req_speed.set(m->drive.speed, m->header.stamp);
    req_steer.set(m->drive.steering_angle, m->header.stamp);
  }
  static double age(Clock::time_point t)
  {
    return std::chrono::duration<double>(Clock::now() - t).count();
  }
  void arm(bool value)
  {
    std::lock_guard<std::mutex> l(mu); bool & pending = value ? arm_pending : disarm_pending;
    if(pending) {return;}
    desired_disarm = !value;
    if (value) {
      reconcile_disarm = false;
    } else if (arm_may_arrive) {
      reconcile_disarm = true;
    }
    if(!arm_client->service_is_ready()) {message = "Arm service unavailable"; return;}
    pending = true; (value ? arm_at : disarm_at) = Clock::now();
    auto id = ++(value ? arm_generation : disarm_generation);
    auto req = std::make_shared<std_srvs::srv::SetBool::Request>(); req->data = value;
    ++service_inflight; try {
      auto request = arm_client->async_send_request(req,
        [this, value, id](rclcpp::Client<std_srvs::srv::SetBool>::SharedFuture f){
          bool follow_disarm = false;
          {std::lock_guard<std::mutex> l(mu); --service_inflight;
            auto & generation = value ? arm_generation : disarm_generation; if(id == generation) {
              (value ? arm_pending : disarm_pending) = false; try {
                auto r = f.get();
                message = QString(value ? "Arm: " : "Disarm: ") +
                (r->success ? "accepted: " : "rejected: ") + QString::fromStdString(r->message);
              } catch(const std::exception & e) {
                message = e.what();
              }
            }
            if (value && id == arm_generation) {arm_may_arrive = arm_outcome_unknown;}
            follow_disarm = value && desired_disarm && !disarm_pending;}
          if(follow_disarm) {arm(false);}
  });
      (value ? arm_request_id : disarm_request_id) = request.request_id;
      if (value) {arm_may_arrive = true;}
    } catch(const std::exception & e) {--service_inflight;pending = false;message = e.what();}
  }
  void reset()
  {
    std::lock_guard<std::mutex> l(mu);
    if(reset_pending) {return;} if(!reset_client->service_is_ready()) {
      message = "Reset service unavailable";return;
    }
    reset_pending = true; reset_at = Clock::now(); auto id = ++reset_generation;
    ++service_inflight; try {
      auto request = reset_client->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>(),
        [this, id](rclcpp::Client<std_srvs::srv::Trigger>::SharedFuture f){
          std::lock_guard<std::mutex> l(mu); --service_inflight; if(id != reset_generation) {
            return;
          }
          reset_pending = false; try {
            auto r = f.get();
            message = QString("Reset: ") + (r->success ? "accepted: " : "rejected: ") +
            QString::fromStdString(r->message);
          } catch(const std::exception & e) {
            message = e.what();
          }
      });
      reset_request_id = request.request_id;
    } catch(const std::exception & e) {--service_inflight;reset_pending = false;message = e.what();}
  }
  // Called with mu held. A request already taken by the executor will still
  // run its callback, which owns the corresponding service_inflight decrement.
  void expire_services()
  {
    auto expire_arm = [&](bool & pending, Clock::time_point at, int64_t id,
        const char * name) {
      if (!pending || age(at) <= 3.0) {return;}
      pending = false;
      if (arm_client->remove_pending_request(id)) {--service_inflight;}
      message = QString(name) + " timed out; outcome unknown";
    };
    if (arm_pending && age(arm_at) > 3.0) {arm_outcome_unknown = true;}
    expire_arm(arm_pending, arm_at, arm_request_id, "Arm");
    expire_arm(disarm_pending, disarm_at, disarm_request_id, "Disarm");
    if (reset_pending && age(reset_at) > 3.0) {
      reset_pending = false;
      if (reset_client->remove_pending_request(reset_request_id)) {--service_inflight;}
      message = "Reset timed out; outcome unknown";
    }
  }
  void start()
  {
    std::lock_guard<std::mutex> l(mu); if(goal_state.pending || goal_state.uncertain || goal) {
      return;
    }
    if(!action->action_server_is_ready()) {message = "Run action unavailable";return;}
    goal_state.request(); start_at = Clock::now(); message = "Start requested";
    auto generation = ++goal_generation;
    rclcpp_action::Client<Action>::SendGoalOptions opts;
    opts.goal_response_callback = [this, generation](Goal::SharedPtr g){
        std::lock_guard<std::mutex> l(mu);if(generation != goal_generation) {
          return;
        }
        goal_state.response(bool(g));goal = g;message = g ? "Run accepted" : "Run rejected";
      };
    opts.result_callback = [this, generation](const Goal::WrappedResult & r){
        std::lock_guard<std::mutex> l(mu);if(generation != goal_generation) {
          return;
        }
        goal.reset();goal_state.result();cancel_pending = false;
        message = r.result ? QString("Run result: ") +
          QString::fromStdString(r.result->message) : "Run ended without result";
      };
    try {action->async_send_goal(Action::Goal(), opts);} catch(const std::exception & e) {
      goal_state.timeout();message = QString("Start failed; outcome unknown: ") + e.what();
    }
  }
  void cancel()
  {
    std::lock_guard<std::mutex> l(mu); if(!goal || cancel_pending) {return;} cancel_pending = true;
    cancel_at = Clock::now();message = "Cancel requested"; auto generation = goal_generation;
    auto id = ++cancel_generation;
    try {
      action->async_cancel_goal(goal,
        [this, generation, id](action_msgs::srv::CancelGoal::Response::SharedPtr r){
          std::lock_guard<std::mutex> l(mu);
          if(generation != goal_generation || id != cancel_generation || !goal) {
            return;
          }
          cancel_pending = false;
          message = r &&
          !r->goals_canceling.empty() ? "Cancel accepted; awaiting result" : "Cancel rejected";
      });
    } catch(const std::exception & e) {cancel_pending = false;message = e.what();}
  }
  std::mutex mu; Status status; bool status_seen = false; Clock::time_point status_at{};
  Sample req_speed, req_steer, cmd_speed, cmd_steer, speed, clearance;
  Obstacle obstacle; Vehicle vehicle; bool obstacle_seen = false, vehicle_seen = false;
  Clock::time_point obstacle_at{}, vehicle_at{};
  bool arm_pending = false, disarm_pending = false, reset_pending = false, cancel_pending = false,
    desired_disarm = true, arm_may_arrive = false, arm_outcome_unknown = false,
    reconcile_disarm = false; GoalState goal_state;
  unsigned service_inflight = 0;
  int64_t arm_request_id = 0, disarm_request_id = 0, reset_request_id = 0;
  Clock::time_point last_reconcile{};
  uint64_t arm_generation = 0, disarm_generation = 0, reset_generation = 0, goal_generation = 0,
    cancel_generation = 0;
  Clock::time_point arm_at{}, disarm_at{}, reset_at{}, start_at{}, cancel_at{}, clock_at{};
  int64_t last_clock = 0; bool simulation; QString message = "No control request sent";
  Goal::SharedPtr goal;
  rclcpp::Node::SharedPtr node; rclcpp::executors::SingleThreadedExecutor executor;
  std::thread thread; std::atomic<bool> stopping{false};
  ImageLiveness raw_image, debug_image;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr raw_sub, debug_sub;
  rclcpp::Client<std_srvs::srv::SetBool>::SharedPtr arm_client; rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr reset_client; rclcpp_action::Client<Action>::SharedPtr action;
  rclcpp::Subscription<Status>::SharedPtr status_sub;
  rclcpp::Subscription<Drive>::SharedPtr auto_sub, manual_sub,
    command_sub; rclcpp::Subscription<Odom>::SharedPtr wheel_sub;
  rclcpp::Subscription<Obstacle>::SharedPtr obstacle_sub;
  rclcpp::Subscription<Vehicle>::SharedPtr vehicle_sub;
};
}  // namespace uamc_dashboard
