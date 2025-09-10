import sys
import firebase_admin
from firebase_admin import firestore, credentials
from crontab import CronTab
from datetime import datetime
import pytz
from pathlib import Path
import socket
import yaml
import getpass
import requests

config = {}
project_path = Path(__file__).absolute().parent
with open("{}/config.yml".format(project_path), 'r') as stream:
    config = yaml.safe_load(stream)

# get current time with timezone from config
def getCurrTime():
    utc_now = datetime.now(pytz.utc)
    zone = pytz.timezone(config.get("timezone"))

    return utc_now.astimezone(zone)

# simple log printer with timestamp
def printLog(args):
    print("({}) {}".format(getCurrTime(), args))

# fetch local ip address using socket
def fetchLocalIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('8.8.8.8', 1)) # connect to google dns
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def fetchPublicIP():
    try:
        ip = requests.get('https://api.ipify.org').text
    except Exception as e:
        ip = None
    return ip

# create data structure for firestore
def dataStruct(machine_id):
    data = {
        "last_update": getCurrTime(),
        "interval_min": int(config.get("interval_minutes")),
        "machine_id": machine_id,
        "group_id": config.get("group_id"),
        "local_ip": fetchLocalIP(),
        "public_ip": fetchPublicIP() if config.get("show_public_ip") else None,
    }
    return data

# command "start" - write uptime data to firestore
def uptimeStart():
    firebase_creds = "{}/{}".format(project_path, config.get("firebase_creds"))
    if not Path(firebase_creds).exists():
        printLog("Firebase credentials not found!")
        return
    cred = credentials.Certificate(firebase_creds)
    app = firebase_admin.initialize_app(cred)
    db = firestore.client(app)

    machine_id = config.get("instance_id") or socket.gethostname()

    printLog("Start write uptime")
    db.collection("machine-uptime").document(machine_id).set(dataStruct(machine_id))
    printLog("Write uptime done")

# command "register" - register this script to cronjob
def registerCron():
    user = getpass.getuser()
    cron = CronTab(user=user)
    virtualenv_path = "{}/{}".format(project_path, config.get("virtualenv")) if config.get("virtualenv") else None

    if virtualenv_path and Path(virtualenv_path).exists():
        command = "{}/bin/python3 {} start >> {}".format(
            virtualenv_path,
            Path(__file__).absolute(),
            "{}/{}".format(project_path, "log.txt"))
    else:
        command = "python3 {} start >> {}".format(Path(__file__).absolute(), Path("log.txt").absolute())

    job = cron.new(command=command, comment="project-uptime")
    job.minute.every(int(config.get("interval_minutes")))
    cron.write()

    printLog("Script has been registered to crontab")

# command "remove" - remove this script from cronjob
def removeCron():
    user = getpass.getuser()
    cron = CronTab(user=user)

    cron.remove_all(comment="project-uptime")
    cron.write()
    
    printLog("Script has been removed from crontab")

# command "help" - show help
def showHelp():
    print("Basic commands")
    print(" start\t\t: trigger update status to firestore")
    print(" register\t: register cron scheduling for this script")
    print(" remove\t\t: remove this script from cron scheduler")

def main():
    known_args = ["start", "register", "remove", "help"]
    if len(sys.argv) > 2 or len(sys.argv) < 2 or sys.argv[1] not in known_args:
        print("Argument invalid! should be: {}".format("|".join(known_args)))
        return
    
    if sys.argv[1] == known_args[0]: uptimeStart()
    elif sys.argv[1] == known_args[1]: registerCron()
    elif sys.argv[1] == known_args[2]: removeCron()
    elif sys.argv[1] == known_args[3]: showHelp()

main()