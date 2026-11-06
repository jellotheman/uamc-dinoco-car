#include "uamc_dashboard/dashboard_panel.hpp"
#include "uamc_dashboard/ros_client.hpp"
#include <rviz_common/config.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QCheckBox>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QTimer>

namespace uamc_dashboard
{
DashboardPanel::DashboardPanel(QWidget *parent)
:rviz_common::Panel(parent)
{
  auto *layout = new QVBoxLayout; simulation_ = new QCheckBox("Simulation");
  simulation_->setChecked(true);timeout_ = new QDoubleSpinBox;timeout_->setRange(0.1, 60);
  timeout_->setDecimals(2);timeout_->setValue(0.75);timeout_->setSuffix(" s");
  auto *settings = new QHBoxLayout;settings->addWidget(simulation_);
  settings->addWidget(new QLabel("Status Timeout"));settings->addWidget(timeout_);
  layout->addLayout(settings);
  context_ = new QComboBox;
  context_->addItem("Simulation", "simulation");
  context_->addItem("Hardware context (unverified)", "hardware");
  auto *context_layout = new QHBoxLayout;
  context_layout->addWidget(new QLabel("Deployment Context"));
  context_layout->addWidget(context_); layout->addLayout(context_layout);
  connect(context_, qOverload<int>(&QComboBox::currentIndexChanged), this, [this]{
      Q_EMIT configChanged();
    });
  status_ = new QLabel;inputs_ = new QLabel;values_ = new QLabel;io_ = new QLabel;
  message_ = new QLabel;for(auto *label:{status_, inputs_, values_, io_, message_}) {
    label->setWordWrap(true);layout->addWidget(label);
  }
  auto *buttons = new QHBoxLayout;auto *run_buttons = new QHBoxLayout;arm_ = new QPushButton("Arm");
  disarm_ = new QPushButton("Disarm");reset_ = new QPushButton("Reset");
  start_ = new QPushButton("Start");cancel_ = new QPushButton("Cancel own run");
  for(auto *b:{arm_, disarm_, reset_}) {
    buttons->addWidget(b);
  }
  for(auto *b:{start_, cancel_}) {
    run_buttons->addWidget(b);
  }
  layout->addLayout(buttons);layout->addLayout(run_buttons);setLayout(layout);
  connect(arm_, &QPushButton::clicked, this, [this]{client_->arm(true);});
  connect(disarm_, &QPushButton::clicked, this, [this]{client_->arm(false);});
  connect(reset_, &QPushButton::clicked, this, [this]{client_->reset();});
  connect(start_, &QPushButton::clicked, this, [this]{client_->start();});
  connect(cancel_, &QPushButton::clicked, this, [this]{client_->cancel();});
  connect(simulation_, &QCheckBox::toggled, this, [this](bool checked){
      if(client_) {
        std::lock_guard<std::mutex> l(client_->mu);
        if(client_->service_inflight || client_->goal || client_->goal_state.pending ||
        client_->goal_state.uncertain || client_->arm_pending || client_->disarm_pending ||
        client_->reset_pending || client_->cancel_pending)
        {
          simulation_->blockSignals(true); simulation_->setChecked(!checked);
          simulation_->blockSignals(false);
          client_->message = "Cannot change simulation setting while an operation is outstanding";
          return;
        }
      }
      restart(); Q_EMIT configChanged();
      });
  connect(timeout_, qOverload<double>(&QDoubleSpinBox::valueChanged), this, [this]{
      Q_EMIT configChanged();
      });
  restart();timer_ = new QTimer(this);
  connect(timer_, &QTimer::timeout, this, [this]{refresh();});timer_->start(100);
}
DashboardPanel::~DashboardPanel() = default;
void DashboardPanel::restart()
{
  bool reconcile = false;
  bool arm_may_arrive = false;
  bool arm_outcome_unknown = false;
  if (client_) {
    std::lock_guard<std::mutex> lock(client_->mu);
    reconcile = client_->reconcile_disarm;
    arm_may_arrive = client_->arm_may_arrive;
    arm_outcome_unknown = client_->arm_outcome_unknown;
  }
  auto next = std::make_unique<Client>(simulation_->isChecked());
  {
    std::lock_guard<std::mutex> lock(next->mu);
    next->reconcile_disarm = reconcile;
    next->arm_may_arrive = arm_may_arrive;
    next->arm_outcome_unknown = arm_outcome_unknown;
  }
  client_ = std::move(next);
}
void DashboardPanel::save(rviz_common::Config config) const
{
  rviz_common::Panel::save(config);config.mapSetValue("Simulation", simulation_->isChecked());
  config.mapSetValue("Status Timeout", timeout_->value());
  config.mapSetValue("Deployment Context", context_->currentData().toString());
}
void DashboardPanel::load(const rviz_common::Config & config)
{
  rviz_common::Panel::load(config);bool sim;float timeout; QString context;
  // Older simulation configurations have no context field.
  context_->setCurrentIndex(0);
  if(config.mapGetString("Deployment Context", &context) && context == "hardware") {
    context_->setCurrentIndex(1);
  }
  if(config.mapGetBool("Simulation", &sim)) {
    simulation_->setChecked(sim);
  }
  if(config.mapGetFloat("Status Timeout", &timeout)) {
    timeout_->setValue(timeout);
  }
}
void DashboardPanel::refresh()
{
  auto & c = *client_;std::lock_guard<std::mutex> l(c.mu);auto timeout = timeout_->value();
  auto expire = [&](bool & p, Clock::time_point t, const char *name){
      if(p && Client::age(t) > 3) {
        p = false;c.message = QString(name) + " timed out; outcome unknown";
      }
    };
  c.expire_services();
  expire(c.cancel_pending, c.cancel_at, "Cancel");
  if(c.goal_state.pending && Client::age(c.start_at) > 3) {
    c.goal_state.timeout();c.message = "Start timed out; outcome unknown; waiting for response";
  }
  bool live = fresh(c.status_seen, c.status_at, Clock::now(), timeout);
  auto ros = c.node->now().nanoseconds();if(ros != c.last_clock) {
    c.last_clock = ros;c.clock_at = Clock::now();
  }
  bool paused = c.simulation && (ros == 0 || Client::age(c.clock_at) > timeout);
  if(!live) {
    status_->setText("Safety: UNKNOWN (status missing or stale)");
    inputs_->setText("Inputs: unknown");
  } else {
    auto & s = c.status;
    status_->setText(QString(
        "Mode: %1 | armed: %2 | running: %3 | obstacle hold: %4\nFault: %5\nHealth: %6 | measured standstill: %7")
      .arg(QString::fromStdString(s.mode)).arg(s.armed ? "yes" : "no").arg(s.running ? "yes" :
        "no").arg(s.obstacle_hold ? "yes" : "no").arg(s.fault.empty() ? "none" :
        QString::fromStdString(s.fault)).arg(s.health_reason.empty() ? "none" :
        QString::fromStdString(s.health_reason)).arg(s.measured_standstill ? "yes" : "no"));
    QString text = "Inputs:";
    if(s.input_names.size() != s.input_fresh.size() ||
      s.input_names.size() != s.input_age_sec.size()) {text += " malformed";} else {
      for(size_t i = 0; i < s.input_names.size(); ++i) {
        text +=
          QString("\n%1: %2 (%3 s)").arg(QString::fromStdString(s.input_names[i])).arg(
            s.input_fresh[i] ? "fresh" : "stale").arg(s.input_age_sec[i]);
      }
    } inputs_->setText(text);
  }
  auto input_fresh = [&](const std::string & name){
      if(!live || c.status.input_names.size() != c.status.input_fresh.size()) {
        return false;
      }
      for(size_t i = 0; i < c.status.input_names.size(); ++i) {
        if(c.status.input_names[i] == name) {
          return bool(c.status.input_fresh[i]);
        }
      }
      return false;
    };
  auto stamped = [&](int64_t stamp){
      double delta = (ros - stamp) * 1e-9;return stamp > 0 && delta <= timeout && delta >= -0.25;
    };
  auto sample = [&](const Sample & v, const char *unit, bool gate){
      return gate && stamped(v.stamp) ? v.text(timeout, unit) : QString("unavailable");
    };
  QString obs = "unavailable";
  if(input_fresh("obstacle") && c.obstacle_seen && Client::age(c.obstacle_at) <= timeout &&
    stamped(c.clearance.stamp) && c.obstacle.valid)
  {
    obs = (c.obstacle.detected ? "detected, " : "clear, ") + c.clearance.text(timeout, "m");
  }
  values_->setText(QString(
      "Requested speed: %1 | steering: %2\nCommanded speed: %3 | steering: %4\nMeasured speed: %5 | measured steering: unavailable\nObstacle: %6")
    .arg(sample(c.req_speed, "m/s",
      input_fresh(c.status.mode == "manual" ? "manual" : "auto"))).arg(sample(c.req_steer, "rad",
      input_fresh(c.status.mode == "manual" ? "manual" : "auto"))).arg(sample(c.cmd_speed, "m/s",
      live)).arg(sample(c.cmd_steer, "rad", live)).arg(sample(c.speed, "m/s",
      input_fresh("wheel"))).arg(obs));
  QString io = "unavailable";
  if(input_fresh("status") && c.vehicle_seen && Client::age(c.vehicle_at) <= timeout &&
    stamped(rclcpp::Time(c.vehicle.header.stamp).nanoseconds()))
  {
    io =
      QString("ready: %1, E-stop: %2, fault: %3; %4").arg(c.vehicle.ready ? "yes" :
        "no").arg(c.vehicle.estop ? "yes" : "no").arg(c.vehicle.fault ? "yes" :
        "no").arg(QString::fromStdString(c.vehicle.reason));
  }
  io_->setText(QString("Vehicle I/O %1: %2\nROS clock: %3").arg(
      context_->currentData().toString() == "simulation" ? "(simulation context / fake in sim)" :
      "(hardware context; unverified)").arg(io).arg(paused ? "paused or absent" : "running"));
  auto image_text = [&](const ImageLiveness & image){
      return !image.seen ? QString("missing") :
             (image.live(Clock::now(), timeout, ros) ? QString("live") : QString("STALE"));
    };
  io_->setText(io_->text() +
      QString("\nRaw image: %1 | lane debug image: %2").arg(image_text(c.raw_image),
      image_text(c.debug_image)));
  message_->setText(c.message + (live && c.status.running &&
    !c.goal ? " (run may be external)" : ""));arm_->setEnabled(live && !c.arm_pending);
  disarm_->setEnabled(!c.disarm_pending);reset_->setEnabled(live && !c.reset_pending);
  start_->setEnabled(c.goal_state.can_start(live, c.status.running));
  cancel_->setEnabled(bool(c.goal) && !c.cancel_pending);
}
}
PLUGINLIB_EXPORT_CLASS(uamc_dashboard::DashboardPanel, rviz_common::Panel)
