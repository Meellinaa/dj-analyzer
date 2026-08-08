import os
import json
import itertools

# Camelot Key Compatibility Checker
def are_camelot_compatible(key1, key2):
    if not key1 or not key2 or key1 == 'Unknown' or key2 == 'Unknown':
        return False
    try:
        num1, let1 = int(key1[:-1]), key1[-1]
        num2, let2 = int(key2[:-1]), key2[-1]
    except Exception:
        return False
        
    # Same key
    if num1 == num2 and let1 == let2:
        return True
    # Adjacent hours (e.g. 8 to 7 or 9)
    if let1 == let2:
        diff = abs(num1 - num2)
        if diff == 1 or diff == 11:  # 11 covers 12 to 1 transition (12 - 1 = 11)
            return True
    # Relative Major/Minor swap (same number, different letter)
    if num1 == num2 and let1 != let2:
        return True
        
    return False

# BPM Compatibility Checker
def check_bpm_compatibility(bpm1, bpm2, max_diff=10.0):
    """
    Checks if two BPMs are close enough to be matched.
    Returns: (is_compatible, target_bpm, mode)
    """
    # Standard tempo matching
    if abs(bpm1 - bpm2) <= max_diff:
        return True, bpm1, "standard"
        
    # Half-time transition (Song A is fast, Song B is slow)
    if abs(bpm1 / 2.0 - bpm2) <= max_diff:
        return True, bpm1, "half_time"
        
    # Double-time transition (Song A is slow, Song B is fast)
    if abs(bpm1 * 2.0 - bpm2) <= max_diff:
        return True, bpm1, "double_time"
        
    return False, bpm1, None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    library_path = os.path.join(script_dir, "library.json")
    playlist_path = os.path.join(script_dir, "playlist.json")
    
    if not os.path.exists(library_path):
        print(f"Error: library.json not found at {library_path}. Please run batch_analyzer.py first.")
        return
        
    with open(library_path, 'r') as f:
        library = json.load(f)
        
    if not library:
        print("Error: library.json is empty. Add songs to Songs/ and analyze them.")
        return
        
    print(f"Loaded {len(library)} tracks from library database.")
    
    track_list = list(library.values())
    
    # Find the optimal order of all tracks using permutations to maximize beatmatched transitions
    best_perm = None
    max_beatmatches = -1
    best_transitions = []
    
    # Since N is small (5 tracks), we can run all permutations (5! = 120) instantly
    for perm in itertools.permutations(track_list):
        beatmatches = 0
        transitions = []
        
        for i in range(len(perm) - 1):
            track_a = perm[i]
            track_b = perm[i+1]
            
            key_compat = are_camelot_compatible(track_a['camelot_key'], track_b['camelot_key'])
            bpm_compat, target_bpm, trans_mode = check_bpm_compatibility(track_a['bpm'], track_b['bpm'])
            
            if key_compat and bpm_compat:
                beatmatches += 1
                transitions.append({
                    "type": "beatmatch",
                    "target_bpm": target_bpm,
                    "mode": trans_mode,
                    "reason": f"Harmonic match ({track_a['camelot_key']} -> {track_b['camelot_key']}) & BPM match ({track_a['bpm']} -> {track_b['bpm']})"
                })
            else:
                transitions.append({
                    "type": "fade",
                    "reason": f"Incompatible: Keys ({track_a['camelot_key']} vs {track_b['camelot_key']}) or BPMs ({track_a['bpm']} vs {track_b['bpm']})"
                })
                
        if beatmatches > max_beatmatches:
            max_beatmatches = beatmatches
            best_perm = perm
            best_transitions = transitions
            
    print(f"\nOptimal playlist order found with {max_beatmatches} beatmatched transitions:")
    
    playlist_output = []
    
    # Print the playlist flow
    for i, track in enumerate(best_perm):
        print(f"[{i+1}] {track['title']} ({track['bpm']} BPM, Key: {track['camelot_key']})")
        
        # Save to output structure
        playlist_output.append({
            "title": track["title"],
            "file_path": track["file_path"],
            "bpm": track["bpm"],
            "key": track["key"],
            "camelot_key": track["camelot_key"],
            "stems_dir": track["stems_dir"],
            "stems": track["stems"],
            "transition_to_next": best_transitions[i] if i < len(best_transitions) else None
        })
        
        if i < len(best_transitions):
            trans = best_transitions[i]
            if trans["type"] == "beatmatch":
                print(f"    >>> BEATMATCH TRANSITION: {trans['reason']} (Target BPM: {trans['target_bpm']})")
            else:
                print(f"    >>> FADE TRANSITION: {trans['reason']}")
                
    # Save to playlist.json
    with open(playlist_path, 'w') as f:
        json.dump(playlist_output, f, indent=2)
        
    print(f"\nPlaylist successfully saved to: {playlist_path}")

if __name__ == "__main__":
    main()
