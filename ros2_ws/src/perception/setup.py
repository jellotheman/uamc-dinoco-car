from setuptools import setup

package_name = 'uamc_perception'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                ('share/' + package_name, ['package.xml'])],
    install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True,
    maintainer='UAMC team', maintainer_email='team@example.com',
    description='Lane and obstacle perception', license='Apache-2.0',
    entry_points={'console_scripts': [
        'lane_detector = uamc_perception.lane_node:main',
        'obstacle_detector = uamc_perception.obstacle_node:main',
    ]},
)
