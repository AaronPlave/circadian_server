import urllib2
import re
import sys
import json
import db
import uuid
import urlparse
import feedparser
from datetime import datetime
feedparser._HTMLSanitizer.acceptable_elements.add("iframe")
# socket.setdefaulttimeout()

# id:"a9c272921e809f861f1951ea6ff1f829"
# secret:@"6d4cea605ed5e4c48bec8a48ef545310"
                  
#     [SCSoundCloud setClientID:@"a9c272921e809f861f1951ea6ff1f829"
#      secret:@"6d4cea605ed5e4c48bec8a48ef545310"
# redirectURL:[NSURL URLWithString:@"Circadian://oauth"]];

# to get a SC api link from a standard SC link,
# curl with resolve, the link, and client_id
# curl 'http://api.soundcloud.com/resolve.json?url=https://soundcloud.com/echocell/babylon-kraddy-remix-1&client_id=a9c272921e809f861f1951ea6ff1f829'

CLIENT_ID = "a9c272921e809f861f1951ea6ff1f829"
CLIENT_SECRET = "6d4cea605ed5e4c48bec8a48ef545310"
TIME_DELTA = 48   #number of hours old

def scrape_new_source(data):
	source_url = data[0]
	user_id = data[1]
	# if we can get an RSS link out of the blog, we can in 
	# theory scrape it (plus, we don't have a way of knowing 
	# if the blog will successfully yield songs since these blogs
	# have highly variable soundcloud link yields to begin with.

	# check source_url
	parsed_url = urlparse.urlparse(source_url)
	if not parsed_url.scheme in ["http","https"]:
		new_source_url = "http://"+source_url
	else:
		new_source_url = source_url
	print "SCRAPER: GETTING RSS URL"
	rss_url = getRSS(new_source_url)
	if rss_url in ("user","server"):
		print "SCRAPER: NO RSS"
		return rss_url

	# figure out title of source by looking at source_url
	tmp_title = parsed_url.hostname
	title = tmp_title if tmp_title else source_url

	# got an RSS so add the source to the db
	sourceID = db.add_source_to_db(source_url=source_url,title=title, rss_url=rss_url)

	# link source and user
	if not db.link_source_and_user(sourceID, user_id):
		return "server"

	# fetch songs from source
	print "SCRAPER: GETTING MUSIC FROM RSS"
	results = getMusicFromRSS(rss_url)
	if results:
		for i in results:
			db.add_song_to_source(i,sourceID)

	# update last update time in status
	db.set_last_update_time(datetime.now())
	return "good",sourceID

def scrape_current_source(data):
	sourceID = data[0]
	rss_url = data[1]

	if not rss_url:
		return False

	results = getMusicFromRSS(rss_url)
	if results:
		for i in results:
			db.add_song_to_source(i,sourceID)

	# Update last update time in status
	db.set_last_update_time(datetime.now())
	return True

def fetchPage(url):
	"""
	Returns the raw data of a page or nothing if unable to fetch
	"""
	try:
		req = urllib2.Request(url, headers={'User-Agent' : "Magic Browser"}) 
		obj = urllib2.urlopen(req)
		raw = obj.read()
		return raw
	except Exception, e:
		print "SCRAPING: Unable to fetch url",url, "ERROR:",e

def resolveURL(url):
	"""
	Checks the url for validity, if invalid, add http://
	"""


def getRSS(blogUrl):
	try:
		# case where the original blog url is bad
		raw = fetchPage(blogUrl)
		if not raw:
			return "user"

		# try to extract an rss link
		pattern = re.compile(r'type="application/rss\+xml".*href=".*"')
		result = pattern.search(raw)

		# if no result, try again but with +"/feed" on the url
		if not result:
			# print "NOPE NO RSS WITH ORIGINAL, TRYING ORIGINAL + /feed"
			result = fetchPage(blogUrl+"/feed")
			if not result:
				# print "NOPE NO RSS HERE"
				return "server"

		match = result.group(0)
		# get the url
		urlPattern = re.compile(r'href=".*?"')
		result2 = urlPattern.search(match)
		match2 = result2.group(0)
		final = match2.split("=")[1]
		final = final[1:len(final)-1]

		# if url does not begin with www or http or https reject
		if "www" in final or "http" in final or "https" in final:
			return final
	except:
		e = sys.exc_info()[0]
		print "SCRAPER: ERROR",e
		return "server"

# MUST BE IN HTTP NOT WWW
blogs = ["http://thissongissick.com/",
		"http://eqmusicblog.com/",'http://gorillavsbear.net',
		'http://abeano.com','http://potholesinmyblog.com',
		'http://prettymuchamazing.com','http://disconaivete.com',
		'http://doandroidsdance.com','http://www.npr.org/blogs/allsongs/',
		'http://blogs.kcrw.com/musicnews/']

urls = ['http://thissongissick.com/blog/feed/', 'http://www.edmsauce.com/feed/', 'http://eqmusicblog.com/feed/', 'http://www.gorillavsbear.net/feed', 'http://www.abeano.com/feed/', None, 'http://prettymuchamazing.com/feed', None, 'http://doandroidsdance.com/feed/', '/rss/rss.php?id', 'http://blogs.kcrw.com/musicnews/feed/']


def isPassed(item):
	# true if item time < 24 from now, else false
	pattern = re.compile(r'<(pubDate|lastBuildDate)>[A-Z]{1}[a-z]{2}, [0-9]{2} [A-Z]{1}[a-z]{2} \d+ \d+:\d+:\d+ \+\d+</(pubDate|lastBuildDate)>')	
	result = pattern.search(item)
	if result == None:
		return False
	match = result.group(0)
	# have to replace the ',' to format correctly for datetime
	if result.group(1) == "pubDate":
		match = match.split("<pubDate>")[1].split("</pubDate>")[0].replace(",","")
	elif result.group(1) == "lastBuildDate":
		match = match.split("<lastBuildDate>")[1].split("</lastBuildDate>")[0].replace(",","")
	m = match.split()
	# getting rid of the timezone field after the hour/min/sec, not supported.
	match = " ".join(m[0:len(m)-1])
	item_time = datetime.strptime(match, '%a %d %b %Y %H:%M:%S')
	current_time = datetime.now()
	delta = current_time - item_time
	hours = (delta.days*24)+(delta.seconds/60.0/60.0)
	return hours < TIME_DELTA

def isFBPassed(item):
	# getting rid of the timezone field after the hour/min/sec, not supported.
	item = item.split()
	item = " ".join(item[0:len(item)-1])
	item_time = datetime.strptime(item, '%a, %d %b %Y %H:%M:%S')
	current_time = datetime.now()
	delta = current_time - item_time
	hours = (delta.days*24)+(delta.seconds/60.0/60.0)
	return hours < TIME_DELTA

def requestTrack(track_id):
	try:
		req = urllib2.urlopen("http://api.soundcloud.com/tracks/"+
							str(track_id)+".json?client_id="+CLIENT_ID)
	except:
		# e = sys.exc_info()[0]
		# print "SCRAPER: Failed to fetch in requestTrack",e,
		return
	response = req.read()
	data = json.loads(response)
	return data

def fromEmbedded(link):
	# returns SC data (i.e. the json object) for the link
	# regex for embedded type of link
	p2 = re.compile(r'tracks(/|%2F)\d+')
	match = p2.search(link)
	if match == None:
		return

	# replacing escaped backslash with /
	track_id = match.group(0).replace("%2F","/")
	track_id = track_id.split("/")[1]
	data = requestTrack(track_id)
	if data == None:
		pass
	return data

def fromStandard(link):
	try:
		req = urllib2.urlopen("http://api.soundcloud.com/resolve.json?url="+link+"&"+"client_id="+CLIENT_ID)
	except:
		e = sys.exc_info()[0]
		print "SCRAPER: Failed to fetch fromStandard",link,e
		return None
	response = req.read()
	data = json.loads(response)
	track_id = data['id']
	data = requestTrack(track_id)
	if data == None:
		pass
	return data

def modifySoundCloudObject(song):
	# Modify stream_url to include CLIENT_ID
	streamUrl = song.get("stream_url")
	if not streamUrl:
		return None
	song["streamURL"] = streamUrl+"?client_id="+CLIENT_ID

	# Add new duplicate fields with different names for Phil
	song["artworkURL"] = song.get("artwork_url") 
	song["date"] = song.get("created_at") 

	user = song.get("user")
	if user:
		song["artist"] = user["username"]
	else:
		song["artist"] = "Unknown Artist" 

	# Generate unique id for the song
	song["_id"] = str(uuid.uuid4())[0:8]
	return song


def getSoundCloudLinks(items):
	# gets the data of each link in each item
	pattern = re.compile(r'https://(w.soundcloud|soundcloud).*?"')
	link_data = [] # list of data dictionaries for each link, unique
	for item in items:
		result = pattern.search(item)
		if result == None:
			# print "No soundcloud links found in this item","soundcloud",item
			continue
		link = result.group(0)
		link = link.replace('"','')
		if result.group(1) == "w.soundcloud":
			data = fromEmbedded(link)
			if data == None:
				continue

			# keep data unique in case multiple copies are matched
			if data not in link_data:
				streamable = modifySoundCloudObject(data)
				if not streamable:
					print "SCRAPER: OH MY GOD NO STREAM URL WHAT DO"
					continue
				link_data.append(streamable)
			else:
				# print "Duplicate track",data['id'],data['title']
				pass
		elif result.group(1) == "soundcloud":
			# MIGHT want to try to filter out links that are to 
			# artist pages and not specific tracks since we can't reall
			# handle those
			data = fromStandard(link)
			if data == None:
				continue
			if data not in link_data:
				streamable = modifySoundCloudObject(data)
				if not streamable:
					print "SCRAPER: OH MY GOD NO STREAM URL WHAT DO"
					continue
				link_data.append(streamable)

	return link_data



def getMusicFromRSS(RSS_URL):
	# looks for links from soundcloud and youtube
	try:
		req = urllib2.Request(RSS_URL, headers={'User-Agent' : "Magic Browser"}) 
		obj = urllib2.urlopen(req)
		raw = obj.read()
	except:
		e = sys.exc_info()[0]
		print "SCRAPER: Failed to fetch main RSS",RSS_URL,e
		return

	#MIGHT want to do a quick regex search for soundcloud to make 
	#sure there's at least one link in there?
	if "soundcloud" not in raw:
		print "SCRAPER: No mention of soundcloud in the entire page, skipping this source:",RSS_URL
		return

	# split by item
	items = raw.split("<item>")[1:]

	# see if it's a feedburner type rss feed..
	if not items or "feedburner" in RSS_URL or "feedburner" in obj.url:
		# print "SCRAPER: Trying feedburner"
		parsed = feedparser.parse(raw)
		entries = parsed["entries"]
		currentItems = []
		for e in entries:
			if isFBPassed(e["published"]):
				currentItems.append(e["content"][0]["value"])	

	# generic RSS method
	else:
		# print "SCRAPER: Generic RSS method"
		#filter out items based on time
		currentItems = []
		for l in items:
			if isPassed(l):
				currentItems.append(l)

	if currentItems:
		# scan for SC links.
		soundcloud_data = getSoundCloudLinks(currentItems)
		print "SCRAPER: SUCCESS ON",RSS_URL," # SONGS:",len(soundcloud_data)
		return soundcloud_data
	else:
		print "SCRAPER: SUCCESS ON",RSS_URL," # SONGS: 0, no current items."
		return


# blogs = ["http://thissongissick.com",
#         "http://eqmusicblog.com",'http://gorillavsbear.net',
#         'http://potholesinmyblog.com', 'http://prettymuchamazing.com',
#         'http://disconaivete.com', 'http://doandroidsdance.com',
#         'http://www.npr.org/blogs/allsongs/','http://blogs.kcrw.com/musicnews/',
#         "http://www.edmsauce.com"]

# [getMusicFromRSS(getRSS(i)) for i in blogs]
