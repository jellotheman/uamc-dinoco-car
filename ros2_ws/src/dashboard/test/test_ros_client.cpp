#include "uamc_dashboard/ros_client.hpp"
#include <gtest/gtest.h>
#include <atomic>
using namespace uamc_dashboard;
using namespace std::chrono_literals;

template<class Predicate> bool wait_for(Predicate predicate)
{
  auto end = Clock::now() + std::chrono::seconds(5);
  while(Clock::now() < end) {if(predicate()) {return true;} std::this_thread::sleep_for(20ms);}
  return false;
}

TEST(RosClient, FakeServersAndPendingDestruction) {
 int argc = 0; char **argv = nullptr;
 if(!rclcpp::ok()) {rclcpp::init(argc, argv);}
  {
    Client absent(false);
    absent.start(); absent.arm(false);
    std::lock_guard<std::mutex> l(absent.mu);
    EXPECT_TRUE(absent.message.contains("unavailable"));
 }
 auto server = std::make_shared<rclcpp::Node>("dashboard_fake_server");
 std::atomic<bool> reject{true};
 auto service = server->create_service<std_srvs::srv::SetBool>("/safety/arm",
      [](const std::shared_ptr<std_srvs::srv::SetBool::Request> req,
      std::shared_ptr<std_srvs::srv::SetBool::Response> response) {
        response->success = true; response->message = req->data ? "armed" : "disarmed";
  });
 std::shared_ptr<rclcpp_action::ServerGoalHandle<Action>> held_goal;
 auto action_server = rclcpp_action::create_server<Action>(server, "/round1/run",
      [&reject](const rclcpp_action::GoalUUID &, std::shared_ptr<const Action::Goal>){
        return reject ? rclcpp_action::GoalResponse::REJECT :
               rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  },
      [](const std::shared_ptr<rclcpp_action::ServerGoalHandle<Action>>) {
        return rclcpp_action::CancelResponse::ACCEPT;
                                                                                                                       },
      [&held_goal](const std::shared_ptr<rclcpp_action::ServerGoalHandle<Action>> goal) {
        held_goal = goal;
                                                                                                          });
 rclcpp::executors::SingleThreadedExecutor executor; executor.add_node(server);
 std::atomic<bool> stop{false}; std::thread server_thread([&]{
      while(!stop) {
        executor.spin_some();std::this_thread::sleep_for(10ms);
      }
    });
  {
    Client client(false);
    EXPECT_TRUE(wait_for([&]{
        return client.action->action_server_is_ready() && client.arm_client->service_is_ready();
                                                                                                                     }));
    client.arm(true);
    EXPECT_TRUE(wait_for([&]{
        std::lock_guard<std::mutex> l(client.mu);
        return !client.arm_pending && client.message.contains("accepted");
                                                                                                                                        }));
    client.start();
    EXPECT_TRUE(wait_for([&]{
        std::lock_guard<std::mutex> l(client.mu);
        return !client.goal_state.pending && client.message.contains("rejected");
                                                                                                                                               }));
    reject = false; client.start();
    EXPECT_TRUE(wait_for([&]{std::lock_guard<std::mutex> l(client.mu);return bool(client.goal);}));
    client.cancel();
    EXPECT_TRUE(wait_for([&]{
        std::lock_guard<std::mutex> l(client.mu);return !client.cancel_pending;
                                                                                                    }));
 }
 stop = true; server_thread.join(); executor.remove_node(server);
}


template<class Predicate> bool wait_for_short(Predicate predicate)
{
  auto end = Clock::now() + std::chrono::seconds(2);
  while(Clock::now() < end) {if(predicate()) {return true;} std::this_thread::sleep_for(20ms);}
  return false;
}

// Advance the request age to exercise expiration without a long wall-clock wait.
TEST(RosClient, RetryIgnoresLateServiceResponse) {
 int argc = 0; char **argv = nullptr;
 if(!rclcpp::ok()) {rclcpp::init(argc, argv);}
 auto server = std::make_shared<rclcpp::Node>("dashboard_retry_server");
 auto group = server->create_callback_group(rclcpp::CallbackGroupType::Reentrant);
 std::atomic<int> count{0};
 std::atomic<bool> old_completed{false};
 auto service = server->create_service<std_srvs::srv::SetBool>("/safety/arm",
      [&count, &old_completed](const std::shared_ptr<std_srvs::srv::SetBool::Request>,
      std::shared_ptr<std_srvs::srv::SetBool::Response> response) {
        int n = ++count;
        if(n == 1) {std::this_thread::sleep_for(500ms);}
        response->success = true;
        response->message = n == 1 ? "old response" : "new response";
        if(n == 1) {old_completed = true;}
  }, rclcpp::ServicesQoS(), group);
 rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), 2);
 executor.add_node(server);
 std::thread server_thread([&]{executor.spin();});
  {
    Client client(false);
    EXPECT_TRUE(wait_for_short([&]{return client.arm_client->service_is_ready();}));
    client.arm(false);
    EXPECT_TRUE(wait_for_short([&]{return count.load() >= 1;}));
    {
      std::lock_guard<std::mutex> l(client.mu);
      client.disarm_at -= std::chrono::seconds(4);
      client.expire_services();
      EXPECT_FALSE(client.disarm_pending);
      EXPECT_EQ(client.service_inflight, 0u);
    }
    client.arm(false);
    EXPECT_TRUE(wait_for_short([&]{
        std::lock_guard<std::mutex> l(client.mu);
        return !client.disarm_pending && client.message.contains("new response");
                                                                            }));
    EXPECT_TRUE(wait_for_short([&]{
        std::lock_guard<std::mutex> l(client.mu);
        return client.service_inflight == 0;
                                     }));
    EXPECT_TRUE(wait_for_short([&]{return old_completed.load();}));
    {
      std::lock_guard<std::mutex> l(client.mu);
      EXPECT_TRUE(client.message.contains("new response"));
      EXPECT_FALSE(client.disarm_pending);
    }
 }
 executor.cancel();
 server_thread.join();
 executor.remove_node(server);
}

TEST(RosClient, LateArmResponseRequestsDisarmAgain) {
 int argc = 0; char **argv = nullptr;
 if(!rclcpp::ok()) {rclcpp::init(argc, argv);}
 auto server = std::make_shared<rclcpp::Node>("dashboard_disarm_server");
 auto group = server->create_callback_group(rclcpp::CallbackGroupType::Reentrant);
 std::atomic<int> arms{0}, disarms{0};
 std::atomic<bool> armed{false};
 auto service = server->create_service<std_srvs::srv::SetBool>("/safety/arm",
      [&](const std::shared_ptr<std_srvs::srv::SetBool::Request> req,
      std::shared_ptr<std_srvs::srv::SetBool::Response> response) {
        if(req->data) {
          ++arms;
          std::this_thread::sleep_for(500ms);
          armed = true;
        } else {
          ++disarms;
          armed = false;
        }
        response->success = true;
        response->message = req->data ? "armed" : "disarmed";
  }, rclcpp::ServicesQoS(), group);
 rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), 2);
 executor.add_node(server);
 std::thread server_thread([&]{executor.spin();});
  {
    Client client(false);
    EXPECT_TRUE(wait_for_short([&]{return client.arm_client->service_is_ready();}));
    client.arm(true);
    EXPECT_TRUE(wait_for_short([&]{return arms.load() == 1;}));
    {
      std::lock_guard<std::mutex> lock(client.mu);
      client.arm_at -= std::chrono::seconds(4);
      client.expire_services();
      EXPECT_FALSE(client.arm_pending);
      EXPECT_EQ(client.service_inflight, 0u);
    }
    client.arm(false);
    EXPECT_TRUE(wait_for_short([&]{return disarms.load() >= 1;}));
    EXPECT_TRUE(wait_for_short([&]{return armed.load();}));
    auto publisher = server->create_publisher<Status>("/safety/status", 10);
    EXPECT_TRUE(wait_for_short([&]{
        Status status;
        status.armed = armed.load();
        publisher->publish(status);
        std::lock_guard<std::mutex> l(client.mu);
        return disarms.load() >= 2 && client.service_inflight == 0;
                                                          }));
    EXPECT_FALSE(armed.load());
 }
 executor.cancel();
 server_thread.join();
 executor.remove_node(server);
}
