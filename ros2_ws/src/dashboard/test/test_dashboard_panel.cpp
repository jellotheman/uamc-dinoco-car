#include "uamc_dashboard/dashboard_panel.hpp"
#include <rviz_common/config.hpp>
#include <rclcpp/rclcpp.hpp>
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <gtest/gtest.h>

TEST(DashboardPanel, ContextAndClockAreSavedIndependently) {
  int argc = 1; char arg[] = "dashboard_test"; char *argv[] = {arg, nullptr};
  if (!rclcpp::ok()) {rclcpp::init(argc, argv);}
  QApplication app(argc, argv);
  uamc_dashboard::DashboardPanel panel;
  auto *clock = panel.findChild<QCheckBox *>();
  auto *context = panel.findChild<QComboBox *>();
  ASSERT_NE(clock, nullptr); ASSERT_NE(context, nullptr);
  rviz_common::Config real;
  real.mapSetValue("Simulation", false);
  real.mapSetValue("Deployment Context", "hardware");
  panel.load(real);
  EXPECT_FALSE(clock->isChecked());
  EXPECT_EQ(context->currentData().toString(), "hardware");
  clock->setChecked(true);
  rviz_common::Config saved;
  panel.save(saved);
  bool sim = false; QString identity;
  ASSERT_TRUE(saved.mapGetBool("Simulation", &sim));
  ASSERT_TRUE(saved.mapGetString("Deployment Context", &identity));
  EXPECT_TRUE(sim);
  EXPECT_EQ(identity, "hardware");
  rviz_common::Config legacy;
  legacy.mapSetValue("Simulation", true);
  panel.load(legacy);
  EXPECT_TRUE(clock->isChecked());
  EXPECT_EQ(context->currentData().toString(), "simulation");
}
