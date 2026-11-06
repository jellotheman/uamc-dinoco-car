#pragma once
#include <rviz_common/panel.hpp>
#include <memory>
class QComboBox; class QLabel; class QPushButton; class QCheckBox; class QDoubleSpinBox; class QTimer;
namespace uamc_dashboard
{
class Client;
class DashboardPanel : public rviz_common::Panel {
  Q_OBJECT

public:
  explicit DashboardPanel(QWidget * parent = nullptr);
  ~DashboardPanel() override;
  void save(rviz_common::Config config) const override;
  void load(const rviz_common::Config & config) override;

private:
  void refresh(); void restart();
  std::unique_ptr<Client> client_;
  QLabel * status_; QLabel * inputs_; QLabel * values_; QLabel * io_; QLabel * message_;
  QPushButton * arm_; QPushButton * disarm_; QPushButton * reset_; QPushButton * start_;
  QPushButton * cancel_;
  QComboBox * context_; QCheckBox * simulation_; QDoubleSpinBox * timeout_; QTimer * timer_;
};
}
