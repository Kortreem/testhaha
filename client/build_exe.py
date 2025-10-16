import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'client.py',
    '--onefile',
    '--console',
    '--name=DriverClient',
    '--add-data=hardware_detector.py;.',
    '--add-data=driver_installer.py;.',
    '--hidden-import=requests',
    '--hidden-import=psutil',
    '--hidden-import=cpuinfo',
    '--clean'
])