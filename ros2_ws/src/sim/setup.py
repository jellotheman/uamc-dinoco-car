from glob import glob
from setuptools import setup

package_name = 'uamc_sim'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/worlds', glob('worlds/*')),
        ('share/' + package_name + '/config', glob('config/*')),
    ],
    install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True,
    maintainer='UAMC team', maintainer_email='team@example.com',
    description='Harmonic practice world and watchdog adapter', license='Apache-2.0',
    entry_points={'console_scripts': ['ackermann_adapter = uamc_sim.ackermann_adapter:main', 'gazebo_supervisor = uamc_sim.gazebo_supervisor:main']},
)
