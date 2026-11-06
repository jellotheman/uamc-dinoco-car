from setuptools import find_packages, setup

package_name = 'uamc_io'
setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='UAMC team',
    maintainer_email='team@example.com',
    description='Fail-closed vehicle transport and manual input',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'camera = uamc_io.camera_node:main',
        'vehicle_io = uamc_io.vehicle_io:main',
        'manual_joy = uamc_io.manual_joy:main',
    ]},
)
