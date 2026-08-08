import os
import json
import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment

# Configuration parameters
SONG_BODY_BARS = 16       # Number of bars to play a song solo before starting transition
TRANSITION_BARS = 8       # Number of bars for the transition window
FADE_DURATION_MS = 4000   # Default duration for fade transitions (4 seconds)

# Stem volume adjustments (in dB)
VOL_VOCALS = 1.0
VOL_DRUMS = 0.0
VOL_BASS = -1.0
VOL_OTHER = -2.0

def get_stretched_stem(track_title, stem_name, stem_path, rate, workspace_dir):
    """
    Checks if a time-stretched stem already exists in the cache directory.
    If not, uses librosa to stretch the audio and saves it.
    Returns:
        AudioSegment: The stretched audio segment loaded into pydub.
    """
    # If the rate is essentially 1.0, load the original file directly
    if abs(rate - 1.0) < 0.005:
        return AudioSegment.from_file(stem_path)
        
    cache_dir = os.path.join(workspace_dir, "separated", "stretched", track_title)
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create a unique filename for this stretch rate
    rate_str = f"{rate:.3f}".replace(".", "_")
    out_path = os.path.join(cache_dir, f"{stem_name}_rate_{rate_str}.wav")
    
    if os.path.exists(out_path):
        print(f"  -> Using cached stretched stem: {stem_name} (rate: {rate:.3f})")
        return AudioSegment.from_file(out_path)
        
    print(f"  -> Time-stretching stem: {stem_name} (rate: {rate:.3f})...")
    y, sr = librosa.load(stem_path, sr=None)
    
    # librosa.effects.time_stretch changes speed without changing pitch
    y_stretched = librosa.effects.time_stretch(y, rate=rate)
    
    # Save the stretched audio as a temporary WAV file
    sf.write(out_path, y_stretched, sr)
    return AudioSegment.from_file(out_path)

def load_stems(track, rate, workspace_dir):
    """
    Loads all four stems for a track, time-stretching them if rate != 1.0.
    Returns a dictionary of AudioSegment objects.
    """
    stems = {}
    title = track["title"]
    
    for stem_name, path in track["stems"].items():
        if os.path.exists(path):
            try:
                stems[stem_name] = get_stretched_stem(title, stem_name, path, rate, workspace_dir)
            except Exception as e:
                print(f"Error loading/stretching stem {stem_name} for {title}: {e}")
                stems[stem_name] = AudioSegment.silent(duration=1000)
        else:
            print(f"Warning: Stem {stem_name} not found for {title}. Using silence.")
            stems[stem_name] = AudioSegment.silent(duration=1000)
            
    # Apply volume balances
    stems["vocals"] = stems["vocals"] + VOL_VOCALS
    stems["drums"] = stems["drums"] + VOL_DRUMS
    stems["bass"] = stems["bass"] + VOL_BASS
    stems["other"] = stems["other"] + VOL_OTHER
    
    return stems

def get_beat_times(drum_stem_path, original_bpm, rate):
    """
    Uses librosa to estimate beat timestamps in seconds.
    Adjusts them by the time-stretch rate.
    """
    try:
        y, sr = librosa.load(drum_stem_path, sr=None)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
    except Exception as e:
        print(f"Beat tracking failed: {e}. Falling back to mathematical beat grid.")
        beat_times = []
        
    # If beat tracking returned too few beats, fallback to mathematical intervals
    if len(beat_times) < 10:
        y, sr = librosa.load(drum_stem_path, sr=None)
        duration_sec = librosa.get_duration(y=y, sr=sr)
        bpm = original_bpm
        beat_interval = 60.0 / bpm
        beat_times = np.arange(0, duration_sec, beat_interval)
        
    # Adjust beat timestamps based on stretch rate
    # If rate is 1.1, audio is speeded up, so timestamps are divided by 1.1
    beat_times = beat_times / rate
    return beat_times

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    playlist_path = os.path.join(script_dir, "playlist.json")
    output_mix_path = os.path.join(script_dir, "Songs", "AI_DJ_Mix.mp3")
    
    if not os.path.exists(playlist_path):
        print(f"Error: playlist.json not found at {playlist_path}. Please run playlist_builder.py first.")
        return
        
    with open(playlist_path, 'r') as f:
        playlist = json.load(f)
        
    if not playlist:
        print("Error: playlist.json is empty.")
        return
        
    print(f"Loaded playlist containing {len(playlist)} tracks.")
    
    # Initialize the main mix segment
    main_mix = None
    
    # We will keep track of the remaining audio of the current song to play
    current_stems = None
    current_beat_times = None
    current_bpm = None
    current_track_idx = 0
    current_time_offset_ms = 0 # Offset in the current track's timeline
    
    while current_track_idx < len(playlist):
        track_a = playlist[current_track_idx]
        title_a = track_a["title"]
        print(f"\nProcessing track [{current_track_idx + 1}/{len(playlist)}]: {title_a}")
        
        # 1. Load stems for Track A at its current speed (rate = 1.0 unless it was stretched previously,
        # but in this engine, we always play the body at its native target speed)
        if current_stems is None:
            # This is the starting track of the mix
            current_bpm = track_a["bpm"]
            current_stems = load_stems(track_a, 1.0, script_dir)
            current_beat_times = get_beat_times(track_a["stems"]["drums"], track_a["bpm"], 1.0)
            current_time_offset_ms = 0
            
        # Determine transition details to next track
        next_track_idx = current_track_idx + 1
        has_next = next_track_idx < len(playlist)
        
        # Calculate when to start the transition
        # We start transition after SONG_BODY_BARS (e.g. 16 bars = 64 beats) from the current offset
        transition_start_beat = int(current_time_offset_ms / (60.0 / current_bpm * 1000)) + (SONG_BODY_BARS * 4)
        
        # Ensure we don't exceed the number of beats available
        if transition_start_beat >= len(current_beat_times):
            transition_start_beat = max(0, len(current_beat_times) - (TRANSITION_BARS * 4) - 4)
            
        trans_start_ms = int(current_beat_times[transition_start_beat] * 1000)
        
        # Extract the solo body segment of Track A
        body_vocals = current_stems["vocals"][current_time_offset_ms : trans_start_ms]
        body_drums = current_stems["drums"][current_time_offset_ms : trans_start_ms]
        body_bass = current_stems["bass"][current_time_offset_ms : trans_start_ms]
        body_other = current_stems["other"][current_time_offset_ms : trans_start_ms]
        
        body_mix = body_vocals.overlay(body_drums).overlay(body_bass).overlay(body_other)
        
        if main_mix is None:
            main_mix = body_mix
        else:
            main_mix = main_mix + body_mix
            
        print(f"  Added solo body: {len(body_mix)/1000:.1f}s")
        
        if not has_next:
            # If this is the last track, append the rest of the song and exit
            remaining_vocals = current_stems["vocals"][trans_start_ms:]
            remaining_drums = current_stems["drums"][trans_start_ms:]
            remaining_bass = current_stems["bass"][trans_start_ms:]
            remaining_other = current_stems["other"][trans_start_ms:]
            
            remaining_mix = remaining_vocals.overlay(remaining_drums).overlay(remaining_bass).overlay(remaining_other)
            main_mix = main_mix + remaining_mix
            print(f"  Added remaining track outro: {len(remaining_mix)/1000:.1f}s")
            break
            
        # 2. Prepare Track B and perform the transition
        track_b = playlist[next_track_idx]
        title_b = track_b["title"]
        trans_info = track_a["transition_to_next"]
        
        if trans_info and trans_info["type"] == "beatmatch":
            print(f"  Performing BEATMATCH transition to: {title_b}")
            
            # Target BPM for transition is A's current BPM (standard)
            # Check if there is a half-time or double-time scale factor
            scale_factor = 1.0
            if trans_info["mode"] == "half_time":
                scale_factor = 0.5
                print("    (Applying Half-Time matching: Song B is double tempo)")
            elif trans_info["mode"] == "double_time":
                scale_factor = 2.0
                print("    (Applying Double-Time matching: Song B is half tempo)")
                
            # Stretch rate for B: we need B to match A's tempo * scale_factor
            target_bpm = current_bpm * scale_factor
            rate_b = target_bpm / track_b["bpm"]
            
            # Load stems for B time-stretched
            stems_b = load_stems(track_b, rate_b, script_dir)
            beat_times_b = get_beat_times(track_b["stems"]["drums"], track_b["bpm"], rate_b)
            
            # We align transition starting at beat 0 of B
            start_b_ms = int(beat_times_b[0] * 1000)
            
            # Transition duration in ms (e.g. 8 bars = 32 beats)
            # 1 beat at current_bpm = (60.0 / current_bpm) * 1000 ms
            beat_duration_ms = (60.0 / current_bpm) * 1000
            trans_duration_ms = int((TRANSITION_BARS * 4) * beat_duration_ms)
            
            trans_end_a_ms = trans_start_ms + trans_duration_ms
            end_b_ms = start_b_ms + trans_duration_ms
            
            # Slice stems of A
            vocals_a = current_stems["vocals"][trans_start_ms : trans_end_a_ms]
            drums_a = current_stems["drums"][trans_start_ms : trans_end_a_ms]
            bass_a = current_stems["bass"][trans_start_ms : trans_end_a_ms]
            other_a = current_stems["other"][trans_start_ms : trans_end_a_ms]
            
            # Slice stems of B
            vocals_b = stems_b["vocals"][start_b_ms : end_b_ms]
            drums_b = stems_b["drums"][start_b_ms : end_b_ms]
            bass_b = stems_b["bass"][start_b_ms : end_b_ms]
            other_b = stems_b["other"][start_b_ms : end_b_ms]
            
            # --- STEM CROSSFADING & BASS SWAPPING ---
            # 1. Vocals: A's vocals remain full volume, B's vocals are silent/low
            mixed_vocals = vocals_a.overlay(vocals_b - 20)
            
            # 2. Drums: Crossfade drums over the full transition
            drums_fade_out = drums_a.fade(to_gain=-30.0, start=0, duration=trans_duration_ms)
            drums_fade_in = drums_b.fade(from_gain=-30.0, start=0, duration=trans_duration_ms)
            mixed_drums = drums_fade_out.overlay(drums_fade_in)
            
            # 3. Bass Swap: Crucial step to avoid clash!
            # We do a fast crossfade (bass swap) in the middle of the transition (bar 4 of 8)
            midpoint_ms = int(trans_duration_ms / 2)
            swap_duration_ms = int(beat_duration_ms * 4) # Swap over 1 bar (4 beats)
            
            # Bass A fades out fast around the midpoint
            bass_a_swap = bass_a.fade(to_gain=-30.0, start=midpoint_ms - int(swap_duration_ms/2), duration=swap_duration_ms)
            # Bass A is silent after the swap
            bass_a_swap = bass_a_swap[0:midpoint_ms] + AudioSegment.silent(duration=trans_duration_ms - midpoint_ms)
            
            # Bass B is silent before the swap, and fades in fast around the midpoint
            bass_b_swap = AudioSegment.silent(duration=midpoint_ms) + bass_b[midpoint_ms:]
            bass_b_swap = bass_b_swap.fade(from_gain=-30.0, start=midpoint_ms - int(swap_duration_ms/2), duration=swap_duration_ms)
            
            mixed_bass = bass_a_swap.overlay(bass_b_swap)
            
            # 4. Other (Melodies): Standard crossfade
            other_fade_out = other_a.fade(to_gain=-25.0, start=0, duration=trans_duration_ms)
            other_fade_in = other_b.fade(from_gain=-25.0, start=0, duration=trans_duration_ms)
            mixed_other = other_fade_out.overlay(other_fade_in)
            
            # Overlay all the transitioned stems
            transition_mix = mixed_vocals.overlay(mixed_drums).overlay(mixed_bass).overlay(mixed_other)
            main_mix = main_mix + transition_mix
            
            print(f"  Added beatmatched transition: {len(transition_mix)/1000:.1f}s")
            
            # Update variables for next iteration
            current_stems = stems_b
            current_beat_times = beat_times_b
            current_bpm = target_bpm # Song B is now playing at Song A's BPM (or scaled BPM)
            current_time_offset_ms = end_b_ms
            
        else:
            # Perform a simple FADE transition
            print(f"  Performing FADE transition to: {title_b}")
            
            # Get full mix of track A remaining outro
            out_vocals = current_stems["vocals"][trans_start_ms : trans_start_ms + FADE_DURATION_MS]
            out_drums = current_stems["drums"][trans_start_ms : trans_start_ms + FADE_DURATION_MS]
            out_bass = current_stems["bass"][trans_start_ms : trans_start_ms + FADE_DURATION_MS]
            out_other = current_stems["other"][trans_start_ms : trans_start_ms + FADE_DURATION_MS]
            segment_a = out_vocals.overlay(out_drums).overlay(out_bass).overlay(out_other)
            
            # Load stems for track B at normal speed (rate = 1.0)
            stems_b = load_stems(track_b, 1.0, script_dir)
            beat_times_b = get_beat_times(track_b["stems"]["drums"], track_b["bpm"], 1.0)
            
            in_vocals = stems_b["vocals"][0 : FADE_DURATION_MS]
            in_drums = stems_b["drums"][0 : FADE_DURATION_MS]
            in_bass = stems_b["bass"][0 : FADE_DURATION_MS]
            in_other = stems_b["other"][0 : FADE_DURATION_MS]
            segment_b = in_vocals.overlay(in_drums).overlay(in_bass).overlay(in_other)
            
            # Crossfade the two full segments using pydub's append method
            fade_mix = segment_a.append(segment_b, crossfade=FADE_DURATION_MS)
            main_mix = main_mix + fade_mix
            
            print(f"  Added fade transition: {FADE_DURATION_MS/1000:.1f}s")
            
            # Update variables for next iteration
            current_stems = stems_b
            current_beat_times = beat_times_b
            current_bpm = track_b["bpm"]
            current_time_offset_ms = FADE_DURATION_MS
            
        current_track_idx += 1
        
    # Export the final continuous mix
    print("\nExporting final continuous DJ mix...")
    os.makedirs(os.path.dirname(output_mix_path), exist_ok=True)
    main_mix.export(output_mix_path, format="mp3")
    print(f"Mix successfully exported to: {output_mix_path}")
    print(f"Total mix length: {len(main_mix)/1000/60:.2f} minutes.")

if __name__ == "__main__":
    main()
