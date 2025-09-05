from csv_functions import delete_track
from spotify import get_track_ids

link_to_delete = "https://open.spotify.com/track/xxxxxxxxxxxxxxxxxx"
tracks = get_track_ids(link_to_delete)

for track_id in tracks:
    print(f"https://open.spotify.com/track/{track_id}")
    delete_track(track_id)

print("all tracks deleted")