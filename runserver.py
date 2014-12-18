from flask import Flask,request
from server import sources, db
app = Flask(__name__)


@app.route('/')
def hello():
    return "ALIVE"


####$$$$$$ TEST ####$$$$$$$
test_data = {"songs": [{"title": "BEER", "_id": '1', "imageURL":
                        "http://fcdn.mtbr.com/attachments/lights-night-riding/939033d1416009231-well-well-well-i-have-4500-lumens-well-well-well.jpg"},
                       {"title": "ALKEHAUL!", "_id": '20', "imageURL": "http://fcdn.mtbr.com/attachments/lights-night-riding/939033d1416009231-well-well-well-i-have-4500-lumens-well-well-well.jpg"}]}
import json
@app.route('/test')
def test():
    return json.dumps(test_data)


@app.route('/test2')
def test2():
	return sources.test()


################$$$$$$$$$$$


# add source
@app.route('/add', methods=['GET'])
def add_source():
    return sources.add_source(request.args.get("sourceID"),request.args.get("userID"))

# get songs from user_id
@app.route('/getsongs/<userID>', methods=['GET'])
def get_songs(userID):
    return db.get_user_songs(userID)

if __name__ == '__main__':
    app.run(debug=True)
