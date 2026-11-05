from setuptools import setup

package_name = 'uamc_control'
setup(name=package_name, version='0.1.0', packages=[package_name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                  ('share/' + package_name, ['package.xml'])],
      install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True, maintainer='UAMC Team',
      maintainer_email='team@example.com', description='Round 1 control and safety gate',
      license='Apache-2.0', entry_points={'console_scripts': [
          'safety_gate = uamc_control.safety_gate:main',
          'lane_planner = uamc_control.lane_planner:main',
          'path_controller = uamc_control.path_controller:main']})
