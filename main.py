import os
import sys
import firebase_admin
from firebase_admin import firestore, credentials
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def dataStruct(machine_id: str, last_word: str):
    data = {
        "last_update": datetime.now(),
        "status": "UP",
        "updated_by": machine_id,
        "last_word": last_word
    }
    return data

def main():
    if len(sys.argv) == 2:
        argument = sys.argv[1]
    elif len(sys.argv) > 2 or len(sys.argv) < 2:
        print("Argument invalid! should be: register|uptime|remove")
        return
    
    if argument == "uptime":

        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        app = firebase_admin.initialize_app()
        db = firestore.client()

        machine_id = os.getenv("INSTANCE_ID")

        print(f"{datetime.now()} => Start write uptime")
        db.collection("machine-uptime").document(machine_id).set(dataStruct(machine_id, last_word))
        print(f"{datetime.now()} => Write uptime done")

    elif argument == "register":
        pass
    elif argument == "remove":
        pass

main()