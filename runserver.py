import os
from flask import Flask
from server import scraping, sources
app = Flask(__name__)

@app.route('/')
def hello():
    return "ALIVE"


#### TEST ####
test_data = {"songs": [{"title": "BEER", "_id": 1, "imageURL":
                        "http://fcdn.mtbr.com/attachments/lights-night-riding/939033d1416009231-well-well-well-i-have-4500-lumens-well-well-well.jpg"},
                       {"title": "ALKEHAUL!", "_id": 20, "imageURL": "http://fcdn.mtbr.com/attachments/lights-night-riding/939033d1416009231-well-well-well-i-have-4500-lumens-well-well-well.jpg"}]}
import json


@app.route('/test')
def test():
    return json.dumps(test_data)

# add source


@app.route('/add/<source>', methods=['GET'])
def add_source(source):
    return sources.add_source(source)

# get songs from user_id


@app.route('/getsongs/<userID>', methods=['GET'])
def get_songs(userID):
    return db.get_user_songs(userID)

if __name__ == '__main__':
    app.run(debug=True)
