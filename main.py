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

    cron = CronTab(user="root")
    job = cron.new(command="python3 {} start >> {}".format(Path(__file__).absolute(), Path("log.txt").absolute()))
    job.minute.every(int(config.get("interval_minutes")))
    cron.write()

    printLog("Script has been registered to crontab")

def removeCron():
    
    cron = CronTab(user="root")
    cron.remove_all()
    printLog("Script has been removed from crontab")

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