from calendar import week
from datetime import timedelta
from datetime import date
from datetime import datetime
import datetime as dt
from ftplib import all_errors
from sys import breakpointhook
from xml.dom.minidom import AttributeList
import spotipy
from math import ceil
from spotipy.oauth2 import SpotifyOAuth
import os
import os.path
import json
from dotenv import load_dotenv

load_dotenv('local.env')

scope = "user-follow-read, user-top-read, playlist-modify-private, playlist-read-private, playlist-read-collaborative"
client_id = os.environ['CLIENT_ID']
client_secret = os.environ['CLIENT_SECRET']
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=client_id, client_secret = client_secret,redirect_uri="http://localhost:1084"))

uri=None

def get_date(artist_albums):
    return artist_albums['release_date']


def get_artist_albums(uri): #obsoleted by no_repeats
    i = 0
    all_artist_albums = []
    got_all_artist_albums = False
    while not got_all_artist_albums:
        artist_albums = sp.artist_albums(uri, album_type="single,album", country='US', limit=20, offset=(i*20))
        if artist_albums['items']:
            i += 1
            for album in artist_albums['items']:
                all_artist_albums.append(album)
        else:
            got_all_artist_albums = True
    return all_artist_albums


def get_artist_albums_no_repeats(uri): #uses artist uri to collect all artist albums/singles released
    i = 0
    all_artist_albums = []
    album_names = []
    got_all_artist_albums = False
    while not got_all_artist_albums:
        artist_albums = sp.artist_albums(uri, album_type="single,album", country='US', limit=20, offset=(i*20))
        if artist_albums['items']:
            i += 1
            for album in artist_albums['items']:
                if album['name'] not in album_names:
                    album_names.append(album['name'])
                    all_artist_albums.append(album)
                else:
                    continue
        else:
            got_all_artist_albums = True
    return all_artist_albums 


def get_all_artists_albums(num_artists): #generates list of all followed artist uris to provide artist uri for album/single api requests
    all_albums = []
    loops = -1
    if num_artists != -1:
        loops = ceil(num_artists / 50)
    if loops == 0:
        return all_albums
    got_all_artists = False
    uri = None
    i = 0
    while (not got_all_artists) and ((loops == -1) or (i < loops)): #parameter loops to limit api requests in batches of 50, set i ~ ((i == -1) or~
        i += 1
        results = sp.current_user_followed_artists(limit=50, after=uri)
        if not results['artists']['items']:
            got_all_artists = True
        for idx, item in enumerate(results['artists']['items']):
            #print("processing an artist")
            uri = item['uri'][15:]
            all_artist_albums = get_artist_albums(uri)
            for album in all_artist_albums:
                all_albums.append(album)
    return all_albums


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
    while (not got_all_artists) and ((loops == -1) or (i < loops)): #parameter loops to limit api requests in batches of 50, set i ~ ((i == -1) or~
        i += 1
        results = None
        try:
            results = sp.current_user_followed_artists(limit=50, after=uri) 
        except Exception as e:
            print(e)
        if results:
            if not results['artists']['items']:
                got_all_artists = True
            for idx, item in enumerate(results['artists']['items']):
                #print("processing an artist")
                uri = item['uri'][15:]
                all_artist_albums = get_artist_albums_no_repeats(uri)
                for album in all_artist_albums:
                    all_albums.append(album)   
    return all_albums


def get_all_tracks(num_tracks): #generates list of all followed artist uris to provide artist uri for album/single api requests
    all_tracks = []
    loops = -1
    if num_tracks != -1:
        loops = ceil(num_tracks / 50)
    if loops == 0:
        return all_tracks
    got_all_tracks = False
    i = 0
    #x=0
    while (not got_all_tracks) and ((loops == -1) or (i < loops)): #parameter loops to limit api requests in batches of 50, set i ~ ((i == -1) or~
        tracks = sp.current_user_saved_tracks(limit=50, offset=(i*50))
        i += 1
        if not tracks:
            got_all_tracks = True
        for track in tracks['items']:
            print(track['track']['name'])
            #x += 1
            all_tracks.append(track)
            #print(all_tracks)
    #print(x)
    return all_tracks

def fetch_album_cache(num_artists):
    file_exists = os.path.exists('album_cache.json')
    if file_exists == False:
        f = open("album_cache.json", "w")
        all_albums = get_all_artists_albums_no_repeats(num_artists)
        #all_albums = get_all_artists_albums(num_artists)
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


def fetch_tracks_cache(num_tracks):
    file_exists = os.path.exists('track_cache.json')
    if file_exists == False:
        f = open("track_cache.json", "w")
        all_tracks = get_all_tracks(num_tracks)
        dictionary = {
            "all_tracks" : all_tracks,
        }
        f.write(json.dumps(dictionary))
        return all_tracks
    else:
        f = open('track_cache.json', "r")
        dictionary = json.load(f)
        all_tracks = dictionary["all_tracks"]
        return all_tracks


def recent_album_releases(num_artists): #input -1 for all artists
    all_albums = fetch_album_cache(num_artists) #input -1 for all artists
    all_albums.sort(key=get_date, reverse=True)
    return all_albums


def isRelevant(albumName: str) -> bool: #checks if current album name contains a filter word, (@@repurpose to filter Remix into separate playlist)
    filters = ['TikTok', 'Playlist', 'Indie', 'Remix', 'Trending']
    for filter in filters:
        if filter in albumName:
            return False
    return True


def album_uri_check(album_uris, album):
    for uri in album_uris:# skips if album uri already exists
            if album["uri"] == uri: 
                return True
                

def artist_name_parsing(album, artist_names):#separates out artist names for printing
    for artist in album["artists"]: 
           return artist_names.append(artist['name'])



def print_top_albums(all_albums, count):
    album_uris = []
    x = 0 #print counter set to 0
    duplicate_uri = 0 #counter
    for idx, album in enumerate(all_albums):  # these lines create a table of artist names
        artist_names = []
        skip = False
        skip = album_uri_check(album_uris, album)
        for artist in album["artists"]: 
            artist_names.append(artist['name'])
        if skip:
            duplicate_uri += 1
            continue
        album_uris.append(album['uri'])
        print(x, " ~ ", album['name'], " ~ ", ", ".join(artist_names), " ~ ", album['album_type'], "(", album['total_tracks'], ")", " ~ ", album['release_date'], " ~ ", album['id'])
        x+=1      
        if x == count:
            print("Duplicate URI:", duplicate_uri)
            break


def get_album_track_uri(album): #using album uri, makes an api call for all tracks on album and returns track uris
    tracks = sp.album_tracks(album['uri'], limit=25, offset=0, market='US')
    track_uris = []
    for track in tracks['items']:
        track_uris.append(track['uri'])
    return track_uris

def get_album_track(album): # list of track dictionaries
    album_tracks = sp.album_tracks(album['uri'], limit=25, offset=0, market='US')
    tracks = []
    for track in album_tracks['items']:
        tracks.append(track)
    return tracks

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
        artist_names = []
        skip = False
        skip = album_uri_check(album_uris, album)
        for artist in album["artists"]: 
            artist_names.append(artist['name'])
        if skip:
            duplicate_uri += 1
            continue
        album_uris.append(album['uri'])
        album_track_uris = release_week_check(album, num_days)
        if album_track_uris == None:
            print(album['release_date'])
            break
        for track_uri in album_track_uris:
            track_uris.append(track_uri)
        print(x, " ~ ", album['name'], " ~ ", ", ".join(artist_names), " ~ ", album['album_type'], "(", album['total_tracks'], ")", " ~ ", album['release_date'], " ~ ", album['id'])
        x+=1      
        if x == count_limit:
            print("Duplicate URI:", duplicate_uri)
            break
    return track_uris


def generate_weekly_playlist():
    all_albums = recent_album_releases(-1)
    track_uris = recent_release_track_uri(all_albums, 6, 200)
    now = datetime.now()
    date_time = now.strftime("%Y/%m/%d")
    playlist_name = date.today()
    user_id_resp = sp.me()
    user_id = user_id_resp['id']
    new_playlist = sp.user_playlist_create(user_id, date_time, public=False, collaborative=False, description='New music for the week ending on ' + date_time)
    all_items_on_playlist = int(len(track_uris) / 100) + ((len(track_uris) % 100) > 0)
    for i in range(0, all_items_on_playlist):
        sp.playlist_add_items(new_playlist['id'], track_uris[100*i:100*(i+1)], position=None)


def get_artist_uris_from_track(all_tracks):
    artist_uris = []
    for track in all_tracks:
        #print(track)
        for artist in track['track']['album']:
            artist_uris.append(artist['id'])    
    return artist_uris

def get_playlist_id(playlist_name):
    x=0
    #user_playlists = []
    got_all_playlists = False
    #playlist_names = []
    while not got_all_playlists:
        user_playlists = sp.current_user_playlists(limit=50, offset=x)
        x+=50
        if not user_playlists['items']:
            got_all_playlists = True
        else:
            for playlist in user_playlists['items']:
                if playlist['name'] == playlist_name:
                    #print(playlist)
                    return playlist['id']


def get_playlist_track_uris(playlist_id):
    playlist_track_uris = []
    playlist_tracks = sp.playlist(playlist_id, fields=None, market='US')
    for track in playlist_tracks['tracks']['items']:
        #print(track)
        playlist_track_uris.append(track['track']['id'])
    return playlist_track_uris


def get_monday_date(d=date.today()): 
    #print(dt.timedelta(days=d.weekday()))
    monday = d - dt.timedelta(days=d.weekday()) 
    return monday


def create_discover_weekly_backup():
    playlist_id = get_playlist_id("Discover Weekly")
    playlist_track_uris = get_playlist_track_uris(playlist_id)
    monday = get_monday_date()
    playlist_name = f'DW {monday}'
    user_id = sp.me()['id']
    new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False, collaborative=False, description= f'Discover Weekly backup for {monday} release.')
    all_items_on_playlist = int(len(playlist_track_uris) / 100) + ((len(playlist_track_uris) % 100) > 0)
    for i in range(0, all_items_on_playlist):
        sp.playlist_add_items(new_playlist['id'], playlist_track_uris[100*i:100*(i+1)], position=None)


def get_recommendations():
    track_uris = []
    recs = sp.recommendations(seed_artists=('1He0ZKninbT4FMEV9hUZKn', '4iMO20EPodreIaEl8qW66y', '1uiEZYehlNivdK3iQyAbye','45yEuthJ9yq1rNXAOpBnqM'), seed_genres=None, seed_tracks=None, limit=20, country='US')
    for rec in recs['tracks']:
        track_uris.append(rec['id'])
        print(rec['name'])
    return track_uris

def create_playlist(playlist_name, track_uris):
    user_id = sp.me()['id']
    new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False, collaborative=False, description="Custom Playlist")
    all_items_on_playlist = int(len(track_uris) / 100) + ((len(track_uris) % 100) > 0)
    for i in range(0, all_items_on_playlist):
        sp.playlist_add_items(new_playlist['id'], track_uris[100*i:100*(i+1)], position=None)