from flask import Flask, request
from server import scraping, sources
app = Flask(__name__)


@app.route('/')
def hello():
    return scraping.a

#### TEST ####
@app.route('/test')
def test():
    return '{"schlafly":"beer"}'

#add source
@app.route('/add/<source>',methods=['GET'])
def add_source(source):
	return sources.add_source(source)

#get songs from sources 
@app.route('/getsongs',methods=['POST'])
def get_songs():
	print request

if __name__ == '__main__':
	app.run(debug=True)