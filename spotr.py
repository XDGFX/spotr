import spotipy
import spotipy.util as util
import cred
import requests
from os import path

username = cred.username

scope = 'playlist-read-private playlist-modify-private'
client_id = '8ad6230fc9a9422ebed4007ce352d98e'
client_secret = cred.client_secret

# Modified lines in util.py:
#   try:
#      import webbrowser
#      webbrowser.open(auth_url)
#      print("Opened %s in your browser" % auth_url)
#   except:
# Removed to prevent Python trying to open a webbrowser 

print('Attempting to fetch token...')

token = util.prompt_for_user_token(
    username, scope, client_id, client_secret, redirect_uri="http://localhost")

if token:

    print('Token fetch successful')

    sp = spotipy.Spotify(auth=token)

    print('Requesting playlists...')
    playlists = sp.user_playlists(username)
    
    for playlist in playlists['items']:
        if playlist['name'] == cred.playlist:

            print('Found playlist: ' + cred.playlist)

            playlist_id = playlist['id']

            print('ID: ' + playlist_id)

            data = sp.user_playlist(username, playlist['id'],
                             fields="tracks")

            tracks = data['tracks']['items']

            links = []
            remove = []
            seen = []

            for track in tracks:
                isrc = track['track']['external_ids']['isrc']

                url = "https://api.deezer.com/2.0/track/isrc:" + isrc

                response = requests.get(url)

                if response.status_code != 200:
                    print('Unable to find isrc: ' + isrc)
                else:
                    links.append(response.json()['link'])
                    remove.append(
                        track['track']['uri'].lstrip('spotify:track:'))

            if path.exists(cred.filename):

                print(cred.filename + ' already exists! Appending to file...')

                with open(cred.filename, 'r') as f:
                    seen = f.readlines()

                seen = [line.strip('\n') for line in seen]

            with open(cred.filename, 'a+') as f:
                for link in links:
                    if link not in seen:
                        f.write("%s\n" % link)

            print('Appended tracks to file')

            print('Removing tracks from Spotify...')

            sp.user_playlist_remove_all_occurrences_of_tracks(
                username, playlist_id, remove)

            print('Success!')

else:
    print('No token supplied')