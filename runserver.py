import os
from flask import Flask
from server import scraping, sources
app = Flask(__name__)

MONGO_URL = os.environ.get('MONGO_URL')
if not MONGO_URL:
    MONGO_URL = "mongodb://localhost:27017/rest";

app.config['MONGO_URI'] = MONGO_URL

@app.route('/')
def hello():
    return "ALIVE"


#### TEST ####
test_data = {"songs":[{"title":"BEER","_id":1},{"title":"ALKEHAUL!","_id":20}]}
import json
@app.route('/test')
def test():
    return json.dumps(test_data)

#add source
@app.route('/add/<source>',methods=['GET'])
def add_source(source):
	return sources.add_source(source)

#get songs from user_id 
@app.route('/getsongs/<userID>',methods=['GET'])
def get_songs(userID):
	return db.get_user_songs(userID)

if __name__ == '__main__':
	app.run(debug=True)