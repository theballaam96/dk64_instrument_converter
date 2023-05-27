"""Various fixes to a midi file to make it work."""

from music21 import midi
from shutil import copyfile

def correct_midi(midi_path, debug_mode, log_file):
    """
        Reads the MIDI file and detects any overlapping instructions for the same note.
        TODO: Might be able to convert from music21 to mido since we can detect this information without knowing the starting tick of a note.
    """
    mf = midi.MidiFile()
    mf.open(midi_path, attrib="rb")
    mf.read()
    track_list = []
    error_list = []
    for i, track in enumerate(mf.tracks):
        repeats = []
        start_header = 0
        notes_on = []
        original_events = {}
        previous_delay = None
        error = False
        for j, evt in enumerate(track.events):
            original_events[j] = evt
            if evt.type == "DeltaTime":
                start_header += evt.time
                previous_delay = j
            elif evt.type == 144: # Note_on
                note_index = evt.parameter1
                measure = (start_header / mf.ticksPerQuarterNote) / 4
                if evt.parameter2 > 0: # Turn on note
                    if note_index in notes_on:
                        error = True
                        msg = f"Potential on error. Channel {i}, event {j}, time {start_header}, measure {measure}, note {note_index}, on {notes_on}. Removing {j} and {previous_delay}"
                        error_list.append(msg)
                        if debug_mode:
                            print(msg)
                    else:
                        notes_on.append(note_index)
                elif evt.parameter2 == 0: # Turn off note
                    if note_index not in notes_on:
                        error = True
                        msg = f"Potential off error. Channel {i}, event {j}, time {start_header}, measure {measure}, note {note_index}, on {notes_on}. Removing {j} and {previous_delay}"
                        error_list.append(msg)
                        if debug_mode:
                            print(msg)
                    else:
                        notes_on.remove(note_index)
                if error:
                    error = False
                    repeats = [x for x in repeats if x != j] + [j, previous_delay]
        new_track = [original_events[x] for x in original_events.keys() if x not in repeats]
        track.events = new_track.copy()
        track_list.append(track)
    mf.close()
    mf.open(midi_path, attrib="wb")
    mf.tracks = track_list.copy()
    mf.write()
    mf.close()
    with open(log_file, "a") as fh:
        if len(error_list) == 0:
            fh.write("No overlap errors found\n")
        else:
            fh.write(f"Correcting {len(error_list)} overlap errors:\n")
            for err in error_list:
                fh.write(f"- {err}\n")

def scanForOverlays(file_name: str, new_file: str, debug_mode: bool, log_file: str):
    """Fixes a song so that there are no notes which occur simultaneously, fixing a playback bug in-game."""
    copyfile(file_name, new_file)
    correct_midi(new_file, debug_mode, log_file)