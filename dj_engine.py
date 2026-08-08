import json
import os
from pydub import AudioSegment

# 1. Load library database
with open('library.json', 'r') as f:
    library = json.load(f)

print(f"Loaded {len(library)} tracks from library.json\n")

# 2. Pick Song A (Vocals) and Song B (Beat)
# Use the titles from library.json or the exact library key.
selected_a = "Sean Paul - 4 - 128"
selected_b = "Timber (feat. Ke_ha) - 9 - 128"

# Helper: match by exact key, title, or basename
def find_track(selection):
    if selection in library:
        return library[selection]

    for key, track in library.items():
        if track.get('title') == selection:
            return track
        if os.path.basename(track.get('file_path', '')) == selection:
            return track
        if key.endswith(selection):
            return track
    return None

track_a = find_track(selected_a)
track_b = find_track(selected_b)

if track_a and track_b:
    print(f"Mixing Vocals from: {track_a['title']} ({track_a['bpm']} BPM, Key: {track_a['camelot_key']})")
    print(f"With Beat from: {track_b['title']} ({track_b['bpm']} BPM, Key: {track_b['camelot_key']})")
    
    # 3. Load stems
    vocals_a = AudioSegment.from_file(os.path.join(track_a['stems_dir'], 'vocals.wav'))
    drums_b = AudioSegment.from_file(os.path.join(track_b['stems_dir'], 'drums.wav'))
    bass_b = AudioSegment.from_file(os.path.join(track_b['stems_dir'], 'bass.wav'))
    
    # 4. Layer stems into a mashup
    mashup = drums_b.overlay(bass_b).overlay(vocals_a + 2)
    
    # 5. Export result
    output_path = "Songs/AI_Mashup_Output.mp3"
    mashup.export(output_path, format="mp3")
    print(f"\nMashup successfully created at: {output_path}")
else:
    print("One or both selected tracks were not found in library.json.")
    print(f"Requested: '{selected_a}' and '{selected_b}'")
    print("Available tracks:")
    for key, track in library.items():
        print(f"- key: {key}")
        print(f"  title: {track.get('title')}")
    print("\nUpdate `selected_a` / `selected_b` in dj_engine.py to match the available library entries.")