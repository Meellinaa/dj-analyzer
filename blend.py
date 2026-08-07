import os
from pydub import AudioSegment

# 1. DEFINE PATHS TO YOUR DEMUCS STEMS
stems_dir = '/Users/melinafathi/Desktop/Projects/DJ/separated/htdemucs/Sean Paul - 4 - 128'

vocals_path = os.path.join(stems_dir, 'vocals.wav')
drums_path = os.path.join(stems_dir, 'drums.wav')
bass_path = os.path.join(stems_dir, 'bass.wav')
other_path = os.path.join(stems_dir, 'other.wav')

# 2. LOAD THE SEPARATED AUDIO STEMS
print("Loading stems...")
vocals = AudioSegment.from_file(vocals_path)
drums = AudioSegment.from_file(drums_path)
bass = AudioSegment.from_file(bass_path)
other = AudioSegment.from_file(other_path)

# 3. CREATE A CUSTOM DJ MIX
# Example: Boost the vocals (+3dB) and slightly lower the drums (-2dB)
louder_vocals = vocals + 3
softer_drums = drums - 2

# Layer the stems together (overlaying audio channels)
remix = louder_vocals.overlay(softer_drums).overlay(bass).overlay(other)

# 4. EXPORT THE REMIXED TRACK
output_path = '/Users/melinafathi/Desktop/Projects/DJ/Songs/Sean_Paul_Remix.mp3'
print("Exporting remix...")
remix.export(output_path, format="mp3")

print(f"Done! Your custom remix was saved to: {output_path}")