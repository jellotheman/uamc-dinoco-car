// Optional interactive RViz layout/screenshot check; not run by colcon test.
#include <rclcpp/rclcpp.hpp>
#include <rviz_common/visualization_frame.hpp>
#include <rviz_common/ros_integration/ros_node_abstraction.hpp>
#include <QApplication>
#include <QDockWidget>
#include <QLabel>
#include <QPushButton>
#include <QTimer>
#include <QPixmap>
#include <QPainter>
#include <rviz_common/render_panel.hpp>
#include <rviz_rendering/render_window.hpp>
#include <iostream>

int main(int argc, char **argv)
{
  if (argc < 4) {
    std::cerr << "Usage: dashboard_gui_smoke INPUT.rviz OUTPUT.rviz SCREENSHOT.png [seconds]\n";
    return 2;
  }
  const QString input = argv[1], output = argv[2], screenshot = argv[3];
  const int seconds = argc > 4 ? std::stoi(argv[4]) : 10;
  rclcpp::init(argc, argv);
  QApplication app(argc, argv);
  auto node =
    std::make_shared<rviz_common::ros_integration::RosNodeAbstraction>("rviz_dashboard_smoke");
  node->get_raw_node()->set_parameter(rclcpp::Parameter("use_sim_time", true));
  auto frame = std::make_unique<rviz_common::VisualizationFrame>(node);
  frame->setApp(&app);
  frame->setSplashPath("");
  frame->initialize(node, input);
  frame->resize(1600, 950);
  frame->show();
  QTimer::singleShot(1800, [&] {
      QDockWidget *raw = nullptr, *debug = nullptr, *panel = nullptr, *displays = nullptr;
      for(auto *dock:frame->findChildren<QDockWidget *>()) {
        std::cout << "DOCK " << dock->windowTitle().toStdString() << " area=" << frame->dockWidgetArea(dock) << "\n";
        if(dock->windowTitle() == "Raw camera") {raw = dock;}
        if(dock->windowTitle() == "Lane diagnostics") {debug = dock;}
        if(dock->windowTitle() == "UAMC Dashboard") {panel = dock;}
        if(dock->windowTitle() == "Displays") {displays = dock;}
      }
      if(argc > 5 && std::string(argv[5]) == "arrange" && raw && debug) {
        frame->addDockWidget(Qt::RightDockWidgetArea, raw);
        frame->addDockWidget(Qt::RightDockWidgetArea, debug);
        frame->splitDockWidget(raw, debug, Qt::Vertical);
        raw->show();debug->show();
        frame->resizeDocks({raw, debug}, {420, 420}, Qt::Horizontal);
        frame->resizeDocks({raw, debug}, {390, 390}, Qt::Vertical);
      }
      if(argc > 5 && std::string(argv[5]) == "arrange" && panel && displays) {
        frame->addDockWidget(Qt::LeftDockWidgetArea, panel);
        frame->splitDockWidget(displays, panel, Qt::Vertical);
        frame->resizeDocks({panel, displays}, {380, 380}, Qt::Horizontal);
        frame->resizeDocks({displays, panel}, {220, 600}, Qt::Vertical);
      }
  });
  if(argc > 5 && std::string(argv[5]) == "exercise") {
    for(const auto & step: std::vector<std::pair<int, QString>>{
      {3000, "Arm"}, {4500, "Start"}, {6500, "Cancel own run"}, {8000, "Disarm"}})
    {
      QTimer::singleShot(step.first, [&, text = step.second]{
          for(auto *button:frame->findChildren<QPushButton *>()) {
            if(button->text() == text) {
              std::cout << "CLICK " << text.toStdString() << " enabled=" << button->isEnabled() <<
                "\n";
              button->click();
            }
          }
      });
    }
  }
  QTimer::singleShot(seconds * 1000, [&] {
      for(auto *label:frame->findChildren<QLabel *>()) {
        if(!label->text().isEmpty()) {std::cout << "LABEL " << label->text().toStdString() << "\n";}
      }
    // QWidget::grab excludes native OGRE child windows on WSLg. Capture each
    // actual render target and place it at its original widget position.
      auto capture = frame->grab();
      QPainter painter(&capture);
      int index = 0;
      for(auto *render:frame->findChildren<rviz_common::RenderPanel *>()) {
        const auto image = screenshot + QString(".render%1.png").arg(index++);
        render->getRenderWindow()->captureScreenShot(image.toStdString());
        painter.drawPixmap(render->mapTo(frame.get(), QPoint(0, 0)), QPixmap(image));
      }
      painter.end();
      if(!capture.save(screenshot)) {std::cerr << "Screenshot save failed\n";}
      frame->saveDisplayConfig(output);
      std::cout << "SAVED " << output.toStdString() << "\n";
      app.quit();
  });
  const int result = app.exec();
  frame.reset();
  rclcpp::shutdown();
  return result;
}
