import os
import sys
import firebase_admin
from firebase_admin import firestore, credentials
from dotenv import load_dotenv
from crontab import CronTab
from datetime import datetime
import pytz
from pathlib import Path
import socket
import yaml
import getpass

config = {}
with open("config.yml", 'r') as stream:
    config = yaml.safe_load(stream)

def getCurrTime():
    utc_now = datetime.now(pytz.utc)
    zone = pytz.timezone(config.get("timezone"))

    return utc_now.astimezone(zone)

def printLog(args):
    print("({}) {}".format(getCurrTime(), args))

def dataStruct(machine_id):
    data = {
        "last_update": getCurrTime(),
        "interval_min": int(config.get("interval_minutes")),
        "machine_id": machine_id,
        "group_id": config.get("group_id")
    }
    return data

def uptimeStart():
    cred = credentials.Certificate(config.get("firebase_creds"))
    app = firebase_admin.initialize_app(cred)
    db = firestore.client(app)

    machine_id = config.get("instance_id") or socket.gethostname()

    printLog("Start write uptime")
    db.collection("machine-uptime").document(machine_id).set(dataStruct(machine_id))
    printLog("Write uptime done")

def registerCron():
    user = getpass.getuser()
    cron = CronTab(user=user)

    if config.get("virtualenv"):
        command = "source {}/bin/activate && python3 {} start >> {}".format(
            Path(config.get("virtualenv")).absolute(),
            Path(__file__).absolute(),
            Path("log.txt").absolute())
    else:
        command = "python3 {} start >> {}".format(Path(__file__).absolute(), Path("log.txt").absolute())

    job = cron.new(command=command, comment="project-uptime")
    job.minute.every(int(config.get("interval_minutes")))
    cron.write()

    printLog("Script has been registered to crontab")

def removeCron():
    user = getpass.getuser()
    cron = CronTab(user=user)

    cron.remove_all(comment="project-uptime")
    
    printLog("Script has been removed from crontab")

def showHelp():
    print("Basic commands")
    print(" start\t\t: trigger update status to firestore")
    print(" register\t: register cron scheduling for this script")
    print(" remove\t\t: remove this script from cron scheduler")

def debug():
    print("{}/bin/activate".format(Path(config.get("virtualenv")).absolute()))

def main():
    known_args = ["start", "register", "remove", "help", "debug"]
    if len(sys.argv) > 2 or len(sys.argv) < 2 or sys.argv[1] not in known_args:
        print("Argument invalid! should be: {}".format("|".join(known_args)))
        return
    
    
    if sys.argv[1] == known_args[0]: uptimeStart()
    elif sys.argv[1] == known_args[1]: registerCron()
    elif sys.argv[1] == known_args[2]: removeCron()
    elif sys.argv[1] == known_args[3]: showHelp()
    elif sys.argv[1] == known_args[4]: debug()

main()