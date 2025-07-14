import os
import sys
import firebase_admin
from firebase_admin import firestore, credentials
from dotenv import load_dotenv
from crontab import CronTab
from datetime import datetime
import pytz
from pathlib import Path

load_dotenv()

def getCurrTime():
    utc_now = datetime.now(pytz.utc)
    zone = pytz.timezone(os.getenv("TIME_ZONE"))

    return utc_now.astimezone(zone)

def printLog(args):
    print("({}) {}".format(getCurrTime(), args))

def dataStruct(machine_id):
    data = {
        "last_update": getCurrTime(),
        "status": "UP",
        "updated_by": machine_id
    }
    return data

def uptimeStart():
    cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    app = firebase_admin.initialize_app()
    db = firestore.client()

    machine_id = os.getenv("INSTANCE_ID")

    printLog("Start write uptime")
    db.collection("machine-uptime").document(machine_id).set(dataStruct(machine_id))
    printLog("Write uptime done")

def registerCron():

    cron = CronTab(user="root")
    job = cron.new(command="python3 {} start >> {}".format(Path(__file__).absolute(), Path("log.txt").absolute()))
    job.minute.every(1)
    cron.write()

    printLog("Script has been registered to crontab")

def removeCron():
    
    cron = CronTab(user="root")
    cron.remove_all()
    printLog("Script has been removed from crontab")

def main():
    known_args = ["register", "start", "remove"]
    if len(sys.argv) > 2 or len(sys.argv) < 2 or sys.argv[1] not in known_args:
        print("Argument invalid! should be: {}".format("|".join(known_args)))
        return
    
    if sys.argv[1] == "start": uptimeStart()
    elif sys.argv[1] == "register": registerCron()
    elif sys.argv[1] == "remove": removeCron()

main()