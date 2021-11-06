import datetime
import logging
import typing
from os import path

import requests
import spotipy
from tqdm import tqdm

import cred

logging.basicConfig(level=logging.INFO)

# Retrieve info from cred.py
username = cred.username
client_id = cred.client_id
client_secret = cred.client_secret

scope = "playlist-read-private playlist-modify-private"


class Spotr:
    def __init__(self):
        self.sp = None

    def authenticate(self):
        logging.info("Attempting to authenticate...")

        self.sp = spotipy.Spotify(
            auth_manager=spotipy.oauth2.SpotifyOAuth(
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost",
                open_browser=False,
            )
        )

        return True if self.sp.me() else False

    def get_download_playlist(self) -> str:
        """
        Find the ID of the playlist to download tracks from.
        """
        playlists = self.sp.user_playlists(username)

        for playlist in playlists["items"]:
            if playlist["name"] == cred.playlist:

                logging.info("Found playlist: " + cred.playlist)
                logging.info("ID: " + playlist["id"])

                return playlist["id"]

        logging.error("Unable to find playlist: " + cred.playlist)
        return False

    def get_all_tracks(self, playlist_id: str) -> list:
        """
        Get all tracks from the download playlist.
        """

        logging.info("Getting all tracks from playlist...")

        # Get playlist from id
        playlist = self.sp.user_playlist(username, playlist_id)

        # Calculate how many requests will need to be made to get all tracks
        playlist_length = playlist["tracks"]["total"]
        requests_needed = playlist_length // 100 + 1

        # Get all tracks in playlist
        playlist_tracks = []
        for i in tqdm(range(requests_needed)):
            playlist_tracks += self.sp.playlist_items(playlist["id"], offset=i * 100)[
                "items"
            ]

        assert len(playlist_tracks) == playlist_length, "Not all tracks were retrieved"

        return playlist_tracks

    def convert_to_deezer(self, spotify_tracks: list) -> typing.Tuple[list, list]:
        """
        Convert a list of spotify tracks to a list of deezer tracks.

        Returns a tuple of two lists:
            - The first list contains the deezer track ids
            - The second list contains the corresponding spotify track ids
        """

        logging.info("Converting to deezer...")

        deezer_links = []
        spotify_successful = []

        for track in tqdm(spotify_tracks):
            try:
                isrc = track["track"]["external_ids"]["isrc"]

                url = "https://api.deezer.com/2.0/track/isrc:" + isrc

                response = requests.get(url)

                if response.status_code != 200:
                    logging.warning("Unable to find isrc: " + isrc)
                else:
                    deezer_links.append(response.json()["link"])
                    spotify_successful.append(
                        track["track"]["uri"].lstrip("spotify:track:")
                    )
            except:
                logging.warning(
                    "Track does not have a valid ISRC. Please download manually."
                )
                logging.info(
                    "Track name: "
                    + track["track"]["name"]
                    + " by "
                    + track["track"]["artists"][0]["name"]
                )

        return deezer_links, spotify_successful

    def append_to_download_file(self, deezer_links: list):
        """
        Append the deezer links to the download file.
        """

        seen = []
        if path.exists(cred.filename):

            logging.info(cred.filename + " already exists! Appending to file...")

            with open(cred.filename, "r") as f:
                seen = f.readlines()

            seen = [line.strip("\n") for line in seen]

        with open(cred.filename, "a+") as f:
            f.write("\n")
            for link in deezer_links:
                if link not in seen:
                    f.write(link + "\n")

        logging.info("Appended tracks to file")

    def remove_tracks_from_spotify(self, playlist_id: str, track_ids: list):
        """
        Remove tracks from the download playlist.
        """

        logging.info("Removing tracks from Spotify...")

        # Split the tracks into groups of 100 to prevent 413 error
        track_ids_split = [
            track_ids[i : i + 100] for i in range(0, len(track_ids), 100)
        ]

        for tracks in track_ids_split:
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id, tracks)

        logging.info("Removed tracks from Spotify")


def main():
    # Print runtime info
    logging.info("Running at " + str(datetime.datetime.now()))

    spotr = Spotr()

    # Authenticate Spotify
    if spotr.authenticate():
        logging.info("Authentication successful")
    else:
        logging.critical("Authentication failed")
        exit(1)

    # Get playlist id as specified in cred.py
    if playlist_id := spotr.get_download_playlist():
        logging.info("Download playlist found")
    else:
        logging.critical("Download playlist not found")
        exit(1)

    # Get all tracks from playlist
    if download_tracks := spotr.get_all_tracks(playlist_id):
        logging.info("All tracks found")
    else:
        logging.critical("No tracks found")
        exit(1)

    # Convert to deezer links
    deezer_links, spotify_successful = spotr.convert_to_deezer(download_tracks)

    # Append to download file
    spotr.append_to_download_file(deezer_links)

    # Remove successful tracks from Spotify playlist
    spotr.remove_tracks_from_spotify(playlist_id, spotify_successful)


if __name__ == "__main__":
    main()
