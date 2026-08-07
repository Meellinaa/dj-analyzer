import json
import os
from pydub import AudioSegment

# 1. Load library database
with open('library.json', 'r') as f:
    library = json.load(f)

print(f"Loaded {len(library)} tracks from library.json\n")

# 2. Pick Song A (Vocals) and Song B (Beat)
# Adjust these keys to match exact titles in your library.json!
song_a_key = "Sean Paul - 4 - 128.mp3"
song_b_key = "Timber (feat. Ke_ha) - 9 - 128.mp3"

track_a = library.get(song_a_key)
track_b = library.get(song_b_key)

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
    print("One or both track keys were not found in library.json.")