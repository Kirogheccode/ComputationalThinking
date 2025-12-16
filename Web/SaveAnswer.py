from pymongo import MongoClient
from dotenv import load_dotenv
from auth import login_required
import os
load_dotenv()
MONGDB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGDB_URI)

db = client["test_db"]

cnt = 1
@login_required
def saveAnswerForUser(answer,mode,users):
    global cnt
    try:
        if answer:
            collection = db[users]
            collection.insert_one({"order":f"answer-{cnt}","answer":answer,"mode":mode})
            cnt+=1
            print("Successfully save")
        else:
            print("Can not save dictionary answer !")
    except Exception as e:
        print("Error:",e)

def closeConnection():
    try:
        # CHỈ cố gắng dọn dẹp nếu client còn sống
        db.command("ping")  # kiểm tra còn kết nối
        for name in db.list_collection_names():
            print(name)
            db.drop_collection(name)
        print("All collections dropped")
    except Exception as e:
        print("Skip clearing DB because connection is already closed:", e)

    try:
        client.close()
        print("MongoDB client closed")
    except:
        print("Client already closed")

def queryAnswerForUser(data,users):
    order = data.get('answer_order','')
    collection = db[users]
    result = collection.find_one({"order":order})
    if result:
        if result.get('mode') == "":
            return {
                "reply": result.get("answer"),
                "mode": result.get("mode"),
                "status": "success"
            }
        else:
            return {
                "food_data": result.get("answer"),
                "mode": result.get("mode"),
                "status": "success"
            }
    else:
        return {"status": "unsuccess"}

def resetDB():
    try:
        db.command("ping")  
        for name in db.list_collection_names():
            db.drop_collection(name)
        print("All collections dropped")
    except Exception as e:
        print("Skip clearing DB because connection is already closed:", e)
    
    global cnt
    cnt = 1
    
if __name__ == '__main__':
    closeConnection()