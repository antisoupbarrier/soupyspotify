from datetime import timedelta # Recent Release, DW
from datetime import date #Recent Release, DW
from datetime import datetime #Recent Release
from math import ceil #Recent Release
import time

from ftplib import all_errors
from sys import breakpointhook
from xml.dom.minidom import AttributeList
from requests.exceptions import ReadTimeout
import json

#########################################################################
#    Spotify OAuth Code
###########################################################################

import spotipy #ALL
from spotipy.oauth2 import SpotifyOAuth #OAuth
import os
import os.path
from configparser import ConfigParser
  
config = ConfigParser()
config.read("config.ini")

scope = "user-follow-read, user-top-read, playlist-modify-private, playlist-read-private, playlist-read-collaborative"
client_id = config.get("spotify", "client_id")
client_secret = config.get("spotify", "client_secret")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=client_id, client_secret = client_secret, redirect_uri="http://localhost:1084"), requests_timeout=10, retries=10)

#print(f"Spotify client id: {client_id}")
#print(f"Spotify client secret: {client_secret}")

##################################################################################
#    Recent Releases by followed artists playlist generation
#####################################################################################

uri=None

def get_date(artist_albums):
    return artist_albums['release_date']

def get_artist_albums_no_repeats(uri): #uses artist uri to collect all artist albums/singles released
    i = 0
    all_artist_albums = []
    album_names = []
    got_all_artist_albums = False
    while not got_all_artist_albums:
        try:
            artist_albums = sp.artist_albums(uri, album_type="single,album", country='US', limit=20, offset=(i*20))
            if artist_albums['items']:
                i += 1
                for album in artist_albums['items']:
                    #print(album['name'])
                    if album['name'] not in album_names:
                        album_names.append(album['name'])
                        all_artist_albums.append(album)
                    else:
                        continue
            else:
                got_all_artist_albums = True
        except Exception as e:
            print(e)
            print("Retrying artist albums...")
    return all_artist_albums 


def get_all_artists_albums_no_repeats(num_artists): #generates list of all followed artist uris to provide artist uri for album/single api requests
    all_albums = []
    loops = -1 
    if num_artists != -1:
        loops = ceil(num_artists / 50)
    if loops == 0:
        return all_albums
    got_all_artists = False
    uri = None
    i = 0
    while (not got_all_artists) and ((loops == -1) or (i < loops)):
        i += 1
        results = None
        try:
            results = sp.current_user_followed_artists(limit=50, after=uri)
            #print(results)
        except ReadTimeout:
            print('Spotify timed out... Trying again..')
            results = sp.current_user_followed_artists(limit=50, after=uri)
        if results:
            if not results['artists']['items']:
                got_all_artists = True
            for idx, item in enumerate(results['artists']['items']): #
                uri = item['id']
                all_artist_albums = get_artist_albums_no_repeats(uri)
                for album in all_artist_albums:
                    all_albums.append(album)
    return all_albums


def fetch_album_cache(num_artists): ### use this cache for testing if necessary. modify recent album releases as necessary
    file_exists = os.path.exists('album_cache.json')
    if file_exists == False:
        f = open("album_cache.json", "w")
        all_albums = get_all_artists_albums_no_repeats(num_artists)
        dictionary = {
            "all_albums" : all_albums,
        }
        f.write(json.dumps(dictionary))
        return all_albums
    else:
        f = open('album_cache.json', "r")
        try:
            dictionary = json.load(f)
        except Exception as e:
            print(e)
        all_albums = dictionary["all_albums"]
        return all_albums

def recent_album_releases(num_artists): #input -1 for all artists
    all_albums = get_all_artists_albums_no_repeats(num_artists)
    #all albums = fetch_album_cache(num_artists) ### enables track caching for testing purposes
    all_albums.sort(key=get_date, reverse=True)
    return all_albums


def album_uri_check(album_uris, album):
    for uri in album_uris:# skips if album uri already exists
            if album["uri"] == uri: 
                return True 


def get_album_track_uri(album): #using album uri, makes an api call for all tracks on album and returns track uris
    got_tracks = False
    track_uris = []
    while got_tracks == False:
        try: 
            tracks = sp.album_tracks(album['uri'], limit=25, offset=0, market='US')
            got_tracks = True
            for track in tracks['items']:
                track_uris.append(track['uri'])
        except:
            print("Retrying sp.album_tracks...")
    else:
        return track_uris


def release_week_check(album, num_days):#number of days 
    release_week = timedelta(days=num_days)
    album_iso_date = date.fromisoformat(album['release_date'])
    current_date = date.today()
    if (album_iso_date + release_week) <= current_date: #checks if release is older than 1 week
        return None
    else:
        track_uris = get_album_track_uri(album)
        return track_uris



def recent_release_track_uri(all_albums, num_days, count_limit):# num_days limits results to days before current date. count limit limts overall count
    album_uris = []
    track_uris = []
    x = 0 #print counter set to 0
    duplicate_uri = 0 #counter
    for idx, album in enumerate(all_albums):  # these lines create a table of artist names
        skip = False
        skip = album_uri_check(album_uris, album)
        #artist_names = [] ## unhash these lines to enable artist name parsing for print below
        #for artist in album["artists"]: 
        #    artist_names.append(artist['name'])
        if skip:
            duplicate_uri += 1
            continue
        album_uris.append(album['uri'])
        album_track_uris = release_week_check(album, num_days)
        if album_track_uris == None:
            break
        for track_uri in album_track_uris:
            track_uris.append(track_uri)
        #print(x, " ~ ", album['name'], " ~ ", ", ".join(artist_names), " ~ ", album['album_type'], "(", album['total_tracks'], ")", " ~ ", album['release_date'], " ~ ", album['id'])
        x+=1      
        if x == count_limit:
            #print("Duplicate URI:", duplicate_uri)
            break
    return track_uris


def generate_weekly_playlist():
    num_artists = -1 #-1 for all, artists requested in batches of 50 (limit this while testing)
    num_days = 6
    all_albums = recent_album_releases(num_artists) 
    track_uris = recent_release_track_uri(all_albums, num_days, 300)
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d")
    user_id_resp = sp.me()
    user_id = user_id_resp['id']
    new_playlist = sp.user_playlist_create(user_id, "RW " + date_time, public=False, collaborative=False, description='New music for the week ending on ' + date_time)
    all_items_on_playlist = int(len(track_uris) / 100) + ((len(track_uris) % 100) > 0)
    for i in range(0, all_items_on_playlist):
        sp.playlist_add_items(new_playlist['id'], track_uris[100*i:100*(i+1)], position=None)


####################################################################
#   Discover Weekly Backup, Can be used for Daily Mix backups??
####################################################################

def get_playlist_id(playlist_name):
    print(f"Retrieving playlist {playlist_name}...")
    x=0
    #user_playlists = []
    got_all_playlists = False
    #playlist_names = []
    while not got_all_playlists:
        print("Retrieving 50 playlists...")
        user_playlists = sp.current_user_playlists(limit=50, offset=x)
        print("Retrieved playlists")
        x+=50
        if not user_playlists['items']:
            got_all_playlists = True
        else:
            for playlist in user_playlists['items']:
                if playlist['name'] == playlist_name:
                    print(playlist)
                    return playlist['id']


def get_playlist_track_uris(playlist_id):
    playlist_track_uris = []
    playlist_tracks = sp.playlist(playlist_id, fields=None, market='US')
    print(f"Retrieving {len(playlist_tracks['tracks'])} uris...")
    for track in playlist_tracks['tracks']['items']:
        print(track)
        playlist_track_uris.append(track['track']['id'])
    print("Retrieved uris")
    return playlist_track_uris


def get_monday_date(d=date.today()): 
    monday = d - timedelta(days=d.weekday()) 
    return monday


def create_discover_weekly_backup():
    playlist_id = get_playlist_id('Discover Weekly')
    playlist_track_uris = get_playlist_track_uris(playlist_id)
    monday = get_monday_date()
    playlist_name = f'DW {monday}'
    print(f"Creating playlist {playlist_name}")
    user_id = sp.me()['id']
    new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False, collaborative=False, description= f'Discover Weekly backup for {monday} release.')
    all_items_on_playlist = int(len(playlist_track_uris) / 100) + ((len(playlist_track_uris) % 100) > 0)
    for i in range(0, all_items_on_playlist):
        sp.playlist_add_items(new_playlist['id'], playlist_track_uris[100*i:100*(i+1)], position=None)
    print("Created playlist")

##########################################################################################
##########################################################################################
