# DJ Analyzer

This repository processes music files from the `Songs/` folder and extracts metadata such as BPM, musical key, and Camelot key. It also optionally separates audio stems using Demucs and saves metadata to `library.json`.

## Files

- `batch_analyzer.py` - batch analyzer for all MP3s in `Songs/`
- `analyze.py` - single-file analyzer and Demucs runner
- `blend.py` - (existing script; purpose not documented here)
- `library.json` - metadata output file (ignored by git)
- `separated/` - Demucs stem output directory (ignored by git)
- `Songs/` - input MP3 files

## Setup

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install librosa numpy
   pip install demucs
   ```

3. Run the batch analyzer:
   ```bash
   python3 batch_analyzer.py
   ```

## Notes

- `library.json` is written incrementally as songs are processed.
- `separated/htdemucs/` is used for Demucs stem output.
- Update `.gitignore` if you want to track `library.json` or stem outputs.
