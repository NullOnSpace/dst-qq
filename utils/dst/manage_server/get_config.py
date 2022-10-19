import configparser
import os


CONFIG = configparser.ConfigParser()
pwd = os.getcwd()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CONFIG.read("server.ini")
os.chdir(pwd)

# blocks
STEAM = CONFIG['steam']
DONTSTARVE = CONFIG['dontstarve']

# keys
HOME = STEAM['home']
CLUSTER_NAME = DONTSTARVE['cluster_name']
BACKUP_NAME = DONTSTARVE['backup_name']
SCRIPT_PATH = DONTSTARVE['script_path']

# handled
STEAMCMD_DIR = os.path.join(HOME, STEAM['steamcmd_dir'])
INSTALL_DIR = os.path.join(HOME, DONTSTARVE['install_dir'])
DONTSTARVE_DIR = os.path.join(HOME, DONTSTARVE['dontstarve_dir'])
CLUSTER_DIR = os.path.join(DONTSTARVE_DIR, CLUSTER_NAME)
BACKUP_DIR = os.path.join(DONTSTARVE_DIR, BACKUP_NAME)
SCRIPT_FILE = os.path.join(INSTALL_DIR, SCRIPT_PATH)