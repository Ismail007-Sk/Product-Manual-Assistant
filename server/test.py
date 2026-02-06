from pymongo import MongoClient

uri = "mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/test?retryWrites=true&w=majority"
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
print(client.list_database_names())
