#include "uamc_dashboard/dashboard_state.hpp"
#include <gtest/gtest.h>
#include <limits>
using namespace uamc_dashboard;
TEST(DashboardState, UsesSteadyReceiptTime) {
 auto now = Clock::now();
 EXPECT_FALSE(fresh(false, now, now, 0.75));
 EXPECT_TRUE(fresh(true, now, now + std::chrono::milliseconds(750), 0.75));
 EXPECT_FALSE(fresh(true, now, now + std::chrono::milliseconds(751), 0.75));
 EXPECT_FALSE(available(true, std::numeric_limits<double>::infinity(), now, now, 0.75));
}
TEST(DashboardState, TimedOutGoalCannotBeRetried) {
 GoalState state;
 EXPECT_FALSE(state.can_start(false, false));
 EXPECT_FALSE(state.can_start(true, true));
 state.request(); state.timeout();
 EXPECT_FALSE(state.can_start(true, false));
 state.response(true);
 EXPECT_TRUE(state.owned);
 EXPECT_FALSE(state.can_start(true, false));
 state.result();
 EXPECT_TRUE(state.can_start(true, false));
 state.request();state.response(false);
 EXPECT_TRUE(state.can_start(true, false));
}


TEST(DashboardState, ImageRequiresAdvancingValidSourceStamp) {
 auto now = Clock::now();
 ImageLiveness image;
 EXPECT_FALSE(image.live(now, 0.75, 1000000000LL));
 image.receive(1, 0, now);
 EXPECT_TRUE(image.live(now, 0.75, 1000000000LL));
 auto later = now + std::chrono::seconds(1);
 image.receive(1, 0, later);
 EXPECT_FALSE(image.live(later, 0.75, 1000000000LL));
 image.receive(2, 0, later);
 EXPECT_TRUE(image.live(later, 0.75, 2000000000LL));
 EXPECT_FALSE(image.live(later, 0.75, 3000000000LL));
 image.receive(2, 1000000000U, later);
 EXPECT_FALSE(image.live(later, 0.75, 2000000000LL));
 image.receive(0, 0, later);
 EXPECT_FALSE(image.live(later, 0.75, 2000000000LL));
}
