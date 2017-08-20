from setuptools import setup, find_packages
import sys
import os
from iffmpegmod.config import DATA_DIR

def postinstall():
    
    cmd = "mkdir -p %s/assets" % DATA_DIR
    os.system(cmd)

    cmd = "mkdir -p %s/ramdisk" % DATA_DIR
    os.system(cmd)

    os.system("chmod 777 %s/*" % DATA_DIR)

    cmd = "mount -t tmpfs -o size=128M tmpfs %s/ramdisk" % DATA_DIR
    os.system(cmd)
    
    fstab_fmt = "tmpfs %s/ramdisk tmpfs defaults,noatime,nosuid,mode=0766,size=128m 0 0"
    fstab = fstab_fmt % DATA_DIR
    if open("/etc/fstab").read().find(DATA_DIR+"/ramdisk") == -1:  
        open("/etc/fstab",'a').write("\n%s" % fstab)
      




setup(
    name="industrial_ffmpeg",
    version="0.1",
    packages= find_packages(),
    package_data = {
        '': ['*.json', '*.sh'] 
    }
)

if sys.argv[1] == 'install':
    postinstall()

