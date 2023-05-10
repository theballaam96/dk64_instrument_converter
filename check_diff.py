"""Check difference between original and converted MIDI to get instrument mapping."""

import os
import tkinter as tk
from tkinter import filedialog
import shutil
import json
from mido import MidiFile, MetaMessage, Message

root = tk.Tk()
root.withdraw()

def checkSongDiff(old: str, new: str, template: str):
    """Converts song instruments from one index to another based on the conversion template provided."""
    cv1 = MidiFile(old, clip=True)
    cv2 = MidiFile(new, clip=True)
    cv1_instruments = {}
    cv2_instruments = {}
    midi_files = [cv1, cv2]
    for idx, cv in enumerate(midi_files):
        for track in cv.tracks:
            for msg in track:
                if isinstance(msg, Message):
                    if msg.type == "program_change":
                        if idx == 0:
                            cv1_instruments[msg.channel] = msg.program + 1
                        else:
                            cv2_instruments[msg.channel] = msg.program + 1
    keys = [x for x in cv1_instruments.keys() if x in cv2_instruments.keys()]
    for key in keys:
        old = cv1_instruments[key]
        new = cv2_instruments[key]
        with open(template, "r") as json_f:
            contents = json_f.read()
            json_contents = json.loads(contents)
            json_keys = [int(x) for x in list(json_contents.keys())]
            if old in json_keys:
                expected = json_contents[str(old)]["new_instrument"]
                if expected >= 0:
                    if expected == new:
                        print(f"{old} -> {new} (Expected)")
                    else:
                        print(f"{old} -> {new} (Expected to be {expected})")
                else:
                    print(f"{old} -> {new} (Empty in data)")
            else:
                print(f"{old} -> {new} (Missing from data)")

old_midi = filedialog.askopenfilename()
new_midi = filedialog.askopenfilename()
models = [x.replace(".json","") for x in os.listdir("./data")]
for idx, model in enumerate(models):
    print(f"{idx} - {model}")
accepted = False
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
template = f"data/{models[selected_model]}.json"
checkSongDiff(old_midi, new_midi, template)