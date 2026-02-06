from pymongo import MongoClient

uri = "Your_MongoDB_URI"
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
print(client.list_database_names())
