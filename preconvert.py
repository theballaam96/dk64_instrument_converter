"""Pre-convert MIDI file."""

import os
import tkinter as tk
from tkinter import filedialog
import shutil
import json
from mido import MidiFile, MetaMessage, Message
from midi_fixes import scanForOverlays

root = tk.Tk()
root.withdraw()
old_midi = None

LOG_FILE = "conversion.log"
TEST_MODE = False

def convertInstrument(old: int, template: str, msg: Message) -> int:
    """Convert instrument from old index to new index, referencing the provided template."""
    with open(template, "r") as json_f:
        contents = json_f.read()
        json_contents = json.loads(contents)
        
        if str(old) in json_contents:
            if json_contents[str(old)]["new_instrument"] >= 0:
                with open(LOG_FILE, "a") as fh:
                    fh.write(f"Channel {msg.channel}: {old} -> {json_contents[str(old)]['new_instrument']}\n")
                return json_contents[str(old)]["new_instrument"]
        with open(LOG_FILE, "a") as fh:
            fh.write(f"Channel {msg.channel}: {old} (Not Converted)\n")
        return old



def convertSong(old: str, new: str, template: str):
    """Converts song instruments from one index to another based on the conversion template provided."""
    with open(LOG_FILE, "w") as fh:
        fh.write(f"- Old MIDI: {old}\n")
        fh.write(f"- New MIDI: {new}\n")
    scanForOverlays(old, new, TEST_MODE, LOG_FILE)
    cv1 = MidiFile(new, clip=True)

    for track in cv1.tracks:
        for msg in track:
            if isinstance(msg, Message):
                if msg.type == "program_change":
                    old_type = msg.program
                    msg.program = convertInstrument(old_type + 1, template, msg) - 1
    if not TEST_MODE:
        cv1.save(new)

if not TEST_MODE:
    old_midi = filedialog.askopenfilename()
dir = old_midi.split("/")[:-1]
new_dir = "/".join(dir) + "/dk64_conversions"
if not os.path.exists(new_dir):
    os.mkdir(new_dir)
new_midi = new_dir + "/" + old_midi.split("/")[-1]
models = [x.replace(".json","") for x in os.listdir("./data")]
if not TEST_MODE:
    for idx, model in enumerate(models):
        print(f"{idx} - {model}")
accepted = False
if not TEST_MODE:
    selected_model = None
    while not accepted:
        selected_model = input("ENTER TEMPLATE NUMBER:")
        extra_prompt = f"Please select number between 0 and {len(models) - 1} (inclusive)"
        if selected_model.isnumeric():
            selected_model = int(selected_model)
            if selected_model >= len(models):
                print(f"Model Index too high. {extra_prompt}")
            elif selected_model < 0:
                print(f"Model index must be positive integer. {extra_prompt}")
            else:
                accepted = True
        else:
            print(f"Input must be integer. {extra_prompt}")
        if not accepted:
            selected_model = None
else:
    selected_model = 1
template = f"data/{models[selected_model]}.json"
convertSong(old_midi, new_midi, template)
print(f"Written to {new_midi}")