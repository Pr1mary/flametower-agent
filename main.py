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
import platform
from tinydb import TinyDB
import uuid

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

# create uptime data format for firestore
def uptimeData(machine_id: str):
    curr_time = getCurrTime()
    data = {
        "last_update": curr_time,
        "uptime_since": curr_time,
        "interval_min": int(config.get("interval_minutes")),
        "machine_id": machine_id,
        "group_id": config.get("group_id"),
        "local_ip": fetchLocalIP(),
        "public_ip": fetchPublicIP() if config.get("show_public_ip") else None,
        "os_type": platform.system()
    }
    return data

# create downtime data format for firestore
def downtimeData(machine_id: str, last_found: datetime):
    data = {
        "id": str(uuid.uuid4()),
        "machine_id": machine_id,
        "old_timestamp": last_found,
        "new_timestamp": getCurrTime(),
    }
    return data

# command "ping" - write uptime data to firestore
def uptimePing():
    # setup firebase creds
    firebase_creds = "{}/{}".format(project_path, config.get("firebase_creds"))
    if not Path(firebase_creds).exists():
        printLog("Firebase credentials not found!")
        return
    cred = credentials.Certificate(firebase_creds)
    app = firebase_admin.initialize_app(cred)
    db = firestore.client(app)

    printLog("--- Start write uptime data ---")

    # setup data
    machine_id = config.get("instance_id") or socket.gethostname()
    uptime_data = uptimeData(machine_id)
    
    # setup tiny db
    tinydb = TinyDB("cache.json")
    old_data = tinydb.all()[0] if len(tinydb.all()) else None
    
    # check if there is old data available in local
    printLog("Checking cache data...")
    if old_data:
        
        printLog("Cache data found, getting required exisiting data...")
        
        last_update = datetime.fromisoformat(old_data.get("last_update"))
        start_from = datetime.fromisoformat(old_data.get("uptime_since"))
        interval = old_data.get("interval_min")

        # continue old uptime start time
        uptime_data["uptime_since"] = start_from if start_from else uptime_data["last_update"]

        # write downtime data to firestore if time differences between local data with updated data
        # is more than interval minutes + 30 seconds as acceptable difference 
        time_diff = (uptime_data.get("last_update") - last_update).total_seconds()
        if time_diff > (interval * 60) + 30:
            downtime_data = downtimeData(machine_id, last_update)
            db.collection("machine-downtime").document(downtime_data.get("id")).set(downtime_data)
        
        # remove old data
        tinydb.truncate()
        printLog("Old cache removed")
    
    # write uptime data to firestore
    printLog("Writing to firestore...")
    db.collection("machine-uptime").document(machine_id).set(uptime_data)
    printLog("Write to firestore done")

    # reformat unsupported value so it can be write as json
    for key, val in uptime_data.items():
        if isinstance(val, datetime):
            uptime_data[key] = str(val)

    # write data as local cache
    printLog("Writing to cache...")
    tinydb.insert(uptime_data)
    printLog("Write to cache done")
    
    printLog("--- Write uptime data process done ---")

# command "register" - register this script to cronjob
def registerCron(command:str = None):
    user = getpass.getuser()
    cron = CronTab(user=user)
    virtualenv_path = "{}/{}".format(project_path, config.get("virtualenv")) if config.get("virtualenv") else None

    if virtualenv_path and Path(virtualenv_path).exists():
        command = "{}/bin/python3 {} {} >> {}".format(
            virtualenv_path,
            Path(__file__).absolute(),
            command,
            "{}/{}".format(project_path, "log.txt"))
    else:
        command = "python3 {} {} >> {}".format(
            Path(__file__).absolute(),
            command,
            Path("log.txt").absolute())

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
    known_args = ["ping", "register", "remove", "help"]
    if len(sys.argv) > 2 or len(sys.argv) < 2 or sys.argv[1] not in known_args:
        print("Argument invalid! should be: {}".format("|".join(known_args)))
        return
    
    if sys.argv[1] == known_args[0]: uptimePing()
    elif sys.argv[1] == known_args[1]: registerCron(known_args[0])
    elif sys.argv[1] == known_args[2]: removeCron()
    elif sys.argv[1] == known_args[3]: showHelp()

main()