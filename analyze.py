import os
import subprocess
import librosa
import numpy as np

file_path = '/Users/melinafathi/Desktop/Projects/DJ/Songs/Sean Paul - 4 - 128.mp3'

# 1. RUN DEMUCS AUTOMATICALLY
print("Separating stems with Demucs...")
subprocess.run(["demucs", file_path], check=True)
print("Demucs finished!")

# 2. LOAD AUDIO & ANALYZE BPM / KEY
print("\nAnalyzing BPM and Key...")
y, sr = librosa.load(file_path, sr=None)

# Tempo
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
bpm = tempo[0] if isinstance(tempo, (list, tuple, np.ndarray)) else tempo

# Key estimation
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
chroma_avg = chroma.mean(axis=1)

notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
key_index = np.argmax(chroma_avg)
estimated_key = notes[key_index]

# 3. PRINT RESULTS
print("=" * 30)
print(f"File: {os.path.basename(file_path)}")
print(f"Estimated tempo: {bpm:.1f} BPM")
print(f"Estimated key: {estimated_key}")
print("=" * 30)