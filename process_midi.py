"""
    Processes MIDI and automatically converts it to a bin file.
    Testing for when I convert this to javascript.    
"""

from filecmp import cmp

midi_file = ""
test_bin_file = ""
test_middle_file = ""
output_file = "test.bin"
temp_file = "temp.bin"

class Event:

    def __init__(self):
        self.contents = None
        self.type = 0
        self.abs_time = 0
        self.content_size = 0
        self.delta_time = 0
        self.obsolete_event = False
        self.duration_time = 0

TRACK_LIMIT_BIG = 0x20
TRACK_LIMIT_SMALL = 16
EVENT_LIMIT = 0x30000

def eventInBounds(event_value: int, previous_event_value: int, lower_bound: int, upper_bound: int, status: bool) -> bool:
    if event_value >= lower_bound and event_value < upper_bound:
        return True
    if status:
        if previous_event_value >= lower_bound and previous_event_value < upper_bound:
            return True
    return False

def Flip32Bit(inLong: int) -> int:
    return (((inLong & 0xFF000000) >> 24) | ((inLong & 0x00FF0000) >> 8) | ((inLong & 0x0000FF00) << 8) | ((inLong & 0x000000FF) << 24))

def WriteLongToBuffer(buffer, address, data):
    if isinstance(buffer, list):
        # List
        buffer[address] = ((data >> 24) & 0xFF)
        buffer[address+1] = ((data >> 16) & 0xFF)
        buffer[address+2] = ((data >> 8) & 0xFF)
        buffer[address+3] = ((data) & 0xFF)
    else:
        # Bytes
        buffer.seek(address)
        buffer.write(data.to_bytes(4, "big"))

def printBufferArray(array: list):
    copy = array.copy()
    copy = [x for xi, x in enumerate(copy) if sum(copy[xi:]) > 0]
    print(copy)

def GetVLBytes(vlByteArray, offset, original, alt_pattern, alt_offset, alt_length, includeFERepeats) -> tuple:
    VLVal = 0
    TempByte = None

    while True:
        if alt_pattern is not None:
            TempByte = alt_pattern[alt_offset]
            alt_offset += 1
            if alt_offset == alt_length:
                alt_pattern = None
                alt_offset = 0
                alt_length = 0
        else:
            vlByteArray.seek(offset)
            TempByte = int.from_bytes(vlByteArray.read(1), "big")
            offset += 1
            vlByteArray.seek(offset)
            val = int.from_bytes(vlByteArray.read(1), "big")
            if (TempByte == 0xFE) and (val != 0xFE) and includeFERepeats:
                vlByteArray.seek(offset)
                repeatFirstByte = int.from_bytes(vlByteArray.read(1), "big")
                offset += 1
                vlByteArray.seek(offset)
                repeatDistanceFromBeginningMarker = ((repeatFirstByte << 8) | vlByteArray.int.from_bytes(read(1), "big"))
                offset += 1
                vlByteArray.seek(offset)
                repeatCount = int.from_bytes(vlByteArray.read(1), "big")
                offset += 1
                alt_pattern = [None] * repeatCount
                copy = (offset - 4) - repeatDistanceFromBeginningMarker
                while copy < ((offset - 4) - repeatDistanceFromBeginningMarker) + repeatCount:
                    vlByteArray.seek(copy)
                    alt_pattern[copy - ((offset - 4) - repeatDistanceFromBeginningMarker)] = int.from_bytes(vlByteArray.read(1), "big")
                    copy += 1
                alt_offset = 0
                alt_length = repeatCount
                TempByte = alt_pattern[alt_offset]
                alt_offset += 1
            elif (TempByte == 0xFE) and (val == 0xFE) and includeFERepeats:
                offset += 1
            if (alt_offset == alt_length) and (alt_pattern is not None):
                alt_pattern = None
                alt_offset = 0
                alt_length = 0
        if (TempByte >> 7) == 0x1:
            VLVal += TempByte
            VLVal = VLVal << 8
        else:
            VLVal += TempByte
            break
    original = VLVal
    Vlength = 0
    c = 0
    a = 0
    while True:
        Vlength += (((VLVal >> c) & 0x7F) << a)
        if c == 24:
            break
        c += 8
        a += 7
    return (offset, original, alt_pattern, alt_offset, alt_length, Vlength)

def ReadMidiByte(vlByteArray, offset, altPattern, altOffset, altLength, includeFERepeats) -> tuple:
    returnByte = None
    if altPattern is not None:
        returnByte = altPattern[altOffset]
        altOffset += 1
    else:
        vlByteArray.seek(offset)
        returnByte = int.from_bytes(vlByteArray.read(1), "big")
        offset += 1
        vlByteArray.seek(offset)
        val = int.from_bytes(vlByteArray.read(1), "big")
        if (returnByte == 0xFE) and (val != 0xFE) and includeFERepeats:
            vlByteArray.seek(offset)
            repeatFirstByte = int.from_bytes(vlByteArray.read(1), "big")
            offset += 1
            vlByteArray.seek(offset)
            repeatDistanceFromBeginningMarker = (repeatFirstByte << 8) | int.from_bytes(vlByteArray.read(1), "big")
            offset += 1
            vlByteArray.seek(offset)
            repeatCount = int.from_bytes(vlByteArray.read(1), "big")
            offset += 1

            altPattern = [None] * repeatCount
            copy = (offset - 4) - repeatDistanceFromBeginningMarker
            while copy < ((offset - 4) - repeatDistanceFromBeginningMarker) + repeatCount:
                vlByteArray.seek(copy)
                altPattern[copy - ((offset - 4) - repeatDistanceFromBeginningMarker)] = int.from_bytes(vlByteArray.read(1), "big")
            altOffset = 0
            altLength = repeatCount
            returnByte = altPattern[altOffset]
            altOffset += 1
        elif (returnByte == 0xFE) and (val == 0xFE) and includeFERepeats:
            offset += 1
    if (altOffset == altLength) and (altPattern is not None):
        altPattern = None
        altOffset = 0
        altLength = 0
    return (offset, altPattern, altOffset, altLength, returnByte)

def ReturnVLBytes(value, length) -> tuple:
    subValue1 = (value >> 21) & 0x7F
    subValue2 = (value >> 14) & 0x7F
    subValue3 = (value >> 7) & 0x7F
    subValue4 = (value >> 0) & 0x7F

    if subValue1 > 0:
        newValue = 0x80808000
        newValue |= (subValue1 << 24)
        newValue |= (subValue2 << 16)
        newValue |= (subValue3 << 8)
        newValue |= subValue4
        length = 4
        return (length, newValue)
    elif subValue2 > 0:
        newValue = 0x00808000
        newValue |= (subValue2 << 16)
        newValue |= (subValue3 << 8)
        newValue |= subValue4
        length = 3
        return (length, newValue)
    elif subValue3 > 0:
        newValue = 0x00008000
        newValue |= (subValue3 << 8)
        newValue |= subValue4
        length = 2
        return (length, newValue)
    else:
        length = 1
        return (length, value)

def WriteVLBytes(outFile, value, length, includeFERepeats):
    tempByte = None
    if length == 1:
        tempByte = value & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
    elif length == 2:
        tempByte = (value >> 8) & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
        tempByte = value & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
    elif length == 3:
        tempByte = (value >> 16) & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
        tempByte = (value >> 8) & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
        tempByte = value & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
    else:
        tempByte = (value >> 24) & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
        tempByte = (value >> 8) & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))
        tempByte = value & 0xFF
        outFile.write(tempByte.to_bytes(1, "big"))

def MidiToGEFormat(in_file: str, out_file: str, has_loop: bool, loop_point: int, no_repeaters: bool) -> bool:
    unused_storage = None
    with open(out_file, "wb") as attempt:
        with open(in_file, "rb") as midi:
            numberTracks = 0
            track_events = []
            track_event_count = [0] * TRACK_LIMIT_BIG
            for x in range(TRACK_LIMIT_BIG):
                track_events.append([])
                for y in range(EVENT_LIMIT):
                    track_events[x].append(Event())
            data = midi.read()
            data_size = len(data)
            with open(temp_file, "wb") as temp:
                temp.write(data)
            with open(temp_file, "r+b") as temp:
                temp.seek(0)
                if int.from_bytes(temp.read(4), "big") != 0x4D546864:
                    raise Exception("Invalid Midi Header")
                header_length = int.from_bytes(temp.read(4), "big") # 0x4
                type = int.from_bytes(temp.read(2), "big") # 0x8
                num_tracks = int.from_bytes(temp.read(2), "big") # 0xA
                tempo = int.from_bytes(temp.read(2), "big") # 0xC
                if num_tracks > TRACK_LIMIT_SMALL:
                    print(F"Too many tracks, truncating to {TRACK_LIMIT_SMALL}")
                    num_tracks = TRACK_LIMIT_SMALL
                numberTracks = num_tracks
                if type not in (0, 1):
                    raise Exception("Invalid Midi Type")
                position = 0xE
                repeatPattern = None
                alt_offset = 0
                alt_length = 0
                unknown_shit = False
                highest_abs_time = 0
                highest_abs_time_by_track = [0] * TRACK_LIMIT_SMALL
                for trackNum in range(numberTracks):
                    original = None
                    abs_time = 0
                    temp.seek(position)
                    track_header = int.from_bytes(temp.read(4), "big")
                    if track_header != 0x4D54726B:
                        raise Exception("Invalid Track Midi Header")
                    track_length = int.from_bytes(temp.read(4), "big")
                    position += 8
                    previous_event_value = 0xFF
                    endFlag = False
                    while not endFlag and position < data_size:
                        original = None
                        position, original, repeatPattern, alt_offset, alt_length, timeTag = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                        abs_time += timeTag
                        position, repeatPattern, alt_offset, alt_length, eventVal = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                        status_bit = False
                        if eventVal <= 0x7F: # Continuation
                            status_bit = True
                        else:
                            status_bit = False
                        if eventVal == 0xFF: # Meta Event
                            position, repeatPattern, alt_offset, alt_length, sub_type = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if sub_type == 0x2F: # End of track event
                                abs_time -= timeTag
                                endFlag = True
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            elif sub_type == 0x51: # Set Tempo Event
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            elif sub_type < 0x7F and sub_type not in (0x51, 0x2F): # Various Unused Meta Events
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                for i in range(length):
                                    position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            elif sub_type == 0x7F: # Unused Sequencer Specific Event
                                position, original, repeatPattern, alt_offset, alt_length, length = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                                for i in range(length):
                                    position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0x80, 0x90, status_bit):
                            current_event_value = None
                            note_number = None
                            if status_bit:
                                note_number = eventVal
                                current_event_value = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, note_number = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                current_event_value = eventVal
                            position, repeatPattern, alt_offset, alt_length, velocity = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0x90, 0xA0, status_bit):
                            current_event_value = None
                            note_number = None
                            if status_bit:
                                note_number = eventVal
                                current_event_value = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, note_number = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                current_event_value = eventVal
                            position, repeatPattern, alt_offset, alt_length, velocity = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xB0, 0xC0, status_bit):
                            # Controller Change
                            controller_type = None
                            if status_bit:
                                controller_type = eventVal
                            else:
                                position, repeatPattern, alt_offset, alt_length, controller_type = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            position, repeatPattern, alt_offset, alt_length, controller_value = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xC0, 0xD0, status_bit):
                            # Instrument Change
                            instrument = None
                            if status_bit:
                                instrument = eventVal
                            else:
                                position, repeatPattern, alt_offset, alt_length, instrument = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xD0, 0xE0, status_bit):
                            # Channel Aftertouch
                            amount = None
                            if status_bit:
                                amount = eventVal
                            else:
                                position, repeatPattern, alt_offset, alt_length, amount = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xE0, 0xF0, status_bit):
                            # Pitch Bend
                            value_lsb = None
                            if status_bit:
                                value_lsb = eventVal
                            else:
                                position, repeatPattern, alt_offset, alt_length, value_lsb = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            position, repeatPattern, alt_offset, alt_length, value_lsb = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventVal == 0xF0 or eventVal == 0xF7:
                            position, original, repeatPattern, alt_offset, alt_length, length = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                            for i in range(length):
                                position, repeatPattern, alt_offset, alt_length, ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                        else:
                            if not unknown_shit:
                                unknown_shit = True
                                raise Exception("Invalid Midi Character Found")
                    if abs_time > highest_abs_time:
                        highest_abs_time = abs_time
                    if abs_time > highest_abs_time_by_track[trackNum]:
                        highest_abs_time_by_track[trackNum] = abs_time
                position = 0xE
                repeatPattern = None
                alt_offset = 0
                alt_length = 0
                for trackNum in range(numberTracks):
                    abs_time = 0
                    temp.seek(position)
                    track_header = int.from_bytes(temp.read(4), "big")
                    if track_header != 0x4D54726B:
                        raise Exception("Invalid Track Midi Header")
                    track_length = int.from_bytes(temp.read(4), "big")
                    position += 8
                    previous_event_value = 0xFF
                    endFlag = False
                    didLoop = False
                    if has_loop and loop_point == 0 and highest_abs_time_by_track[trackNum] > 0:
                        track_events[trackNum][track_event_count[trackNum]].type = 0xFF
                        track_events[trackNum][track_event_count[trackNum]].abs_time = 0
                        track_events[trackNum][track_event_count[trackNum]].content_size = 3
                        track_events[trackNum][track_event_count[trackNum]].contents = [0x2E, 0x00, 0xFF]
                        track_events[trackNum][track_event_count[trackNum]].delta_time = 0
                        track_events[trackNum][track_event_count[trackNum]].obsolete_event = False
                        track_event_count[trackNum] += 1
                        didLoop = True
                    while (not endFlag) and (position < data_size):
                        original = None
                        position, original, repeatPattern, alt_offset, alt_length, timeTag = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                        abs_time += timeTag
                        pre_loop_offset = track_event_count[trackNum]
                        track_events[trackNum][track_event_count[trackNum]].delta_time = timeTag
                        track_events[trackNum][track_event_count[trackNum]].obsolete_event = False
                        track_events[trackNum][track_event_count[trackNum]].contents = None
                        track_events[trackNum][track_event_count[trackNum]].abs_time = abs_time
                        if has_loop and (not didLoop) and highest_abs_time_by_track[trackNum] > loop_point:
                            # Handle Looping
                            if abs_time == loop_point:
                                track_events[trackNum][track_event_count[trackNum]].type = 0xFF
                                track_events[trackNum][track_event_count[trackNum]].abs_time = abs_time
                                track_events[trackNum][track_event_count[trackNum]].content_size = 3
                                track_events[trackNum][track_event_count[trackNum]].contents = [0x2E, 0x00, 0xFF]
                                track_events[trackNum][track_event_count[trackNum]].delta_time = timeTag
                                track_events[trackNum][track_event_count[trackNum]].obsolete_event = False
                                track_event_count[trackNum] += 1
                                pre_loop_offset = track_event_count[trackNum]
                                track_events[trackNum][track_event_count[trackNum]].delta_time = 0
                                track_events[trackNum][track_event_count[trackNum]].obsolete_event = False
                                track_events[trackNum][track_event_count[trackNum]].contents = None
                                track_events[trackNum][track_event_count[trackNum]].abs_time = abs_time
                                didLoop = True
                            elif abs_time > loop_point:
                                track_events[trackNum][track_event_count[trackNum]].type = 0xFF
                                track_events[trackNum][track_event_count[trackNum]].abs_time = loop_point
                                track_events[trackNum][track_event_count[trackNum]].content_size = 3
                                track_events[trackNum][track_event_count[trackNum]].contents = [0x2E, 0x00, 0xFF]
                                if track_event_count[trackNum] > 0:
                                    track_events[trackNum][track_event_count[trackNum]].delta_time = loop_point - track_events[trackNum][track_event_count[trackNum] - 1].abs_time
                                else:
                                    track_events[trackNum][track_event_count[trackNum]].delta_time = loop_point
                                track_event_count[trackNum] += 1
                                track_events[trackNum][track_event_count[trackNum]].delta_time = abs_time - loop_point
                                track_events[trackNum][track_event_count[trackNum]].obsolete_event = False
                                track_events[trackNum][track_event_count[trackNum]].contents = None
                                track_events[trackNum][track_event_count[trackNum]].abs_time = abs_time
                                didLoop = True
                        position, repeatPattern, alt_offset, alt_length, eventVal = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                        status_bit = False
                        if eventVal <= 0x7F: # Continuation
                            status_bit = True
                        else:
                            status_bit = False
                        if eventVal == 0xFF: # Meta Event
                            position, repeatPattern, alt_offset, alt_length, sub_type = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if sub_type == 0x2F: # End of Track event
                                endFlag = True
                                if has_loop and highest_abs_time_by_track[trackNum] > loop_point:
                                    previous_event = track_events[trackNum][track_event_count[trackNum] - 1]
                                    if previous_event.type == 0xFF and previous_event.content_size > 0 and previous_event.contents[0] == 0x2E:
                                        track_events[trackNum][track_event_count[trackNum] - 1].type = 0xFF
                                        track_events[trackNum][track_event_count[trackNum] - 1].content_size = 1
                                        track_events[trackNum][track_event_count[trackNum] - 1].contents = [0x2F]
                                    else:
                                        track_events[trackNum][track_event_count[trackNum] + 1].abs_time = highest_abs_time
                                        track_events[trackNum][track_event_count[trackNum] + 1].delta_time = 0
                                        track_events[trackNum][track_event_count[trackNum] + 1].duration_time = track_events[trackNum][pre_loop_offset].duration_time
                                        track_events[trackNum][track_event_count[trackNum] + 1].obsolete_event = track_events[trackNum][pre_loop_offset].obsolete_event
                                        track_events[trackNum][track_event_count[trackNum] + 1].type = 0xFF
                                        track_events[trackNum][track_event_count[trackNum] + 1].content_size = 1
                                        track_events[trackNum][track_event_count[trackNum] + 1].contents = [0x2F]
                                        track_events[trackNum][pre_loop_offset].type = 0xFF
                                        if highest_abs_time > previous_event.abs_time + previous_event.duration_time:
                                            track_events[trackNum][pre_loop_offset].delta_time = highest_abs_time - (previous_event.abs_time + previous_event.duration_time)
                                            track_events[trackNum][pre_loop_offset].abs_time = highest_abs_time
                                        else:
                                            track_events[trackNum][pre_loop_offset].delta_time = 0
                                            track_events[trackNum][pre_loop_offset].abs_time = previous_event.abs_time
                                        track_events[trackNum][pre_loop_offset].content_size = 7
                                        track_events[trackNum][pre_loop_offset].contents = [0x2D, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]
                                        track_events[trackNum][pre_loop_offset].obsolete_event = False
                                        track_event_count[trackNum] += 1
                                else:
                                    track_events[trackNum][pre_loop_offset].type = 0xFF
                                    track_events[trackNum][pre_loop_offset].content_size = 1
                                    track_events[trackNum][pre_loop_offset].contents = [0x2F]
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            elif sub_type == 0x51: # Set Tempo Event
                                track_events[trackNum][pre_loop_offset].type = 0xFF
                                track_events[trackNum][pre_loop_offset].content_size = 4
                                track_events[trackNum][pre_loop_offset].contents = [0x51, None, None, None]
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, track_events[trackNum][pre_loop_offset].contents[1] = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, track_events[trackNum][pre_loop_offset].contents[2] = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                position, repeatPattern, alt_offset, alt_length, track_events[trackNum][pre_loop_offset].contents[3] = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            elif sub_type < 0x7F and sub_type not in (0x51, 0x2F): # Various unused meta events
                                track_events[trackNum][pre_loop_offset].type = 0xFF
                                position, repeatPattern, alt_offset, alt_length, length = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                for i in range(length):
                                    position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].obsolete_event = True
                            elif sub_type == 0x7F: # Unused Sequencer Specific Event
                                track_events[trackNum][pre_loop_offset].type = 0xFF
                                position, original, repeatPattern, alt_offset, alt_length, length = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                                for i in range(length):
                                    position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].obsolete_event = True
                        elif eventInBounds(eventVal, previous_event_value, 0x80, 0x90, status_bit):
                            current_event_value = None
                            note_number = None
                            if status_bit:
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                                note_number = eventVal
                                current_event_value = previous_event_value
                            else:
                                track_events[trackNum][pre_loop_offset].type = eventVal
                                position, repeatPattern, alt_offset, alt_length, note_number = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                current_event_value = eventVal
                            position, repeatPattern, alt_offset, alt_length, velocity = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            test_backwards = track_event_count[trackNum] - 1
                            while test_backwards >= 0:
                                if (track_events[trackNum][test_backwards].type == 0x90 + (current_event_value % 0x10)) and (not track_events[trackNum][test_backwards].obsolete_event):
                                    if track_events[trackNum][test_backwards].contents[0] == note_number:
                                        track_events[trackNum][test_backwards].duration_time = abs_time - track_events[trackNum][test_backwards].abs_time
                                        break
                                test_backwards -= 1
                            track_events[trackNum][pre_loop_offset].duration_time = 0
                            track_events[trackNum][pre_loop_offset].content_size = 2
                            track_events[trackNum][pre_loop_offset].contents = [note_number, velocity]
                            track_events[trackNum][pre_loop_offset].obsolete_event = True

                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0x90, 0xA0, status_bit):
                            current_event_value = None
                            note_number = None
                            if status_bit:
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                                note_number = eventVal
                                current_event_value = previous_event_value
                            else:
                                track_events[trackNum][pre_loop_offset].type = eventVal
                                position, repeatPattern, alt_offset, alt_length, note_number = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                current_event_value = eventVal
                            position, repeatPattern, alt_offset, alt_length, velocity = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            if velocity == 0: # simulate note off
                                test_backwards = track_event_count[trackNum] - 1
                                while test_backwards >= 0:
                                    if track_events[trackNum][test_backwards].type == current_event_value and (not track_events[trackNum][test_backwards].obsolete_event):
                                        if track_events[trackNum][test_backwards].contents[0] == note_number:
                                            track_events[trackNum][test_backwards].duration_time = abs_time - track_events[trackNum][test_backwards].abs_time
                                            break
                                    test_backwards -= 1
                                track_events[trackNum][pre_loop_offset].duration_time = 0
                                track_events[trackNum][pre_loop_offset].content_size = 2
                                track_events[trackNum][pre_loop_offset].contents = [note_number, velocity]
                                track_events[trackNum][pre_loop_offset].obsolete_event = True
                            else:
                                # Check if no note off received, if so, turn it off and restart note
                                test_backwards = track_event_count[trackNum] - 1
                                while test_backwards >= 0:
                                    if track_events[trackNum][test_backwards].type == current_event_value and (not track_events[trackNum][test_backwards].obsolete_event):
                                        if track_events[trackNum][test_backwards].contents[0] == note_number:
                                            if track_events[trackNum][test_backwards].duration_time == 0: # Means unfinished note
                                                track_events[trackNum][test_backwards].duration_time = abs_time - track_events[trackNum][test_backwards].abs_time
                                            break
                                    test_backwards -= 1
                                track_events[trackNum][pre_loop_offset].duration_time = 0
                                track_events[trackNum][pre_loop_offset].content_size = 2
                                track_events[trackNum][pre_loop_offset].contents = [note_number, velocity]
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xB0, 0xC0, status_bit): # Controller change
                            controller_type = None
                            if status_bit:
                                controller_type = eventVal
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, controller_type = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].type = eventVal
                            position, repeatPattern, alt_offset, alt_length, controller_value = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            track_events[trackNum][pre_loop_offset].content_size = 2
                            track_events[trackNum][pre_loop_offset].contents = [controller_type, controller_value]
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xC0, 0xD0, status_bit): # Change instrument
                            instrument = None
                            if status_bit:
                                instrument = eventVal
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, instrument = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].type = eventVal
                            if (eventVal % 0x10) == 9: # Drums in GM
                                instrument = instrument
                            else:
                                instrument = instrument
                            track_events[trackNum][pre_loop_offset].content_size = 1
                            track_events[trackNum][pre_loop_offset].contents = [instrument]
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xD0, 0xE0, status_bit): # Channel aftertouch
                            track_events[trackNum][pre_loop_offset].type = eventVal
                            amount = None
                            if status_bit:
                                amount = eventVal
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, amount = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].type = eventVal
                            track_events[trackNum][pre_loop_offset].content_size = 1
                            track_events[trackNum][pre_loop_offset].contents = [amount]
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventInBounds(eventVal, previous_event_value, 0xE0, 0xF0, status_bit): # Pitch Bend
                            track_events[trackNum][pre_loop_offset].type = eventVal
                            value_lsb = None
                            if status_bit:
                                value_lsb = eventVal
                                track_events[trackNum][pre_loop_offset].type = previous_event_value
                            else:
                                position, repeatPattern, alt_offset, alt_length, value_lsb = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                                track_events[trackNum][pre_loop_offset].type = eventVal
                            position, repeatPattern, alt_offset, alt_length, value_msb = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            track_events[trackNum][pre_loop_offset].content_size = 2
                            track_events[trackNum][pre_loop_offset].contents = [value_lsb, value_msb]
                            if not status_bit:
                                previous_event_value = eventVal
                        elif eventVal in (0xF0, 0xF7):
                            track_events[trackNum][pre_loop_offset].type = eventVal
                            position, original, repeatPattern, alt_offset, alt_length, length = GetVLBytes(temp, position, original, repeatPattern, alt_offset, alt_length, False)
                            for i in range(length):
                                position, repeatPattern, alt_offset, alt_length, unused_storage = ReadMidiByte(temp, position, repeatPattern, alt_offset, alt_length, False)
                            track_events[trackNum][pre_loop_offset].obsolete_event = True
                        else:
                            if not unknown_shit:
                                unknown_shit = True
                                raise Exception("Invalid Midi Character found")
                        track_event_count[trackNum] += 1
                time_offset = 0
                start_position = 0x44
                # Write Headers
                for i in range(numberTracks):
                    size_data = 0
                    loop_start_position = 0
                    found_loop_start = False
                    previous_track_event = 0x0
                    if track_event_count[i] > 0:
                        attempt.write(start_position.to_bytes(4, "big"))
                        for j in range(track_event_count[i]):
                            track_event = track_events[i][j]
                            length_time_delta = 0
                            length_time_delta, time_delta = ReturnVLBytes(track_event.delta_time + time_offset, length_time_delta)
                            if track_event.obsolete_event:
                                time_offset += track_event.delta_time
                            else:
                                if track_event.type == 0xFF and track_event.contents[0] == 0x2E:
                                    found_loop_start = True
                                    loop_start_position = start_position + size_data + 1 + track_event.content_size + length_time_delta
                                time_offset = 0
                                size_data += length_time_delta
                                if track_event.type == 0xFF and track_event.contents[0] == 0x2D:
                                    offset_back = (start_position + size_data) - loop_start_position + 8
                                    track_event.contents[3] = (offset_back >> 24) & 0xFF
                                    track_event.contents[4] = (offset_back >> 16) & 0xFF
                                    track_event.contents[5] = (offset_back >> 8) & 0xFF
                                    track_event.contents[6] = (offset_back >> 0) & 0xFF
                                if track_event.type != previous_track_event or track_event.type == 0xFF:
                                    size_data += 1
                                size_data += track_event.content_size
                                if track_event.type >= 0x90 and track_event.type < 0xA0:
                                    length_duration_bytes = 0
                                    length_duration_bytes, duration = ReturnVLBytes(track_event.duration_time, length_duration_bytes)
                                    size_data += length_duration_bytes
                                previous_track_event = track_event.type
                        start_position += size_data
                    else:
                        attempt.write((0).to_bytes(4, "big"))
                # Write remaining parts of header
                i = numberTracks
                while i < TRACK_LIMIT_SMALL:
                    attempt.write((0).to_bytes(4, "big"))
                    i += 1
                attempt.write(tempo.to_bytes(4, "big"))
                for i in range(numberTracks):
                    # Write track data
                    if track_event_count[i] > 0:
                        previous_track_event = 0
                        for j in range(track_event_count[i]):
                            track_event = track_events[i][j]
                            if track_event.obsolete_event:
                                time_offset += track_event.delta_time
                            else:
                                length_time_delta = 0
                                length_time_delta, time_delta = ReturnVLBytes(track_event.delta_time + time_offset, length_time_delta)
                                time_offset = 0
                                WriteVLBytes(attempt, time_delta, length_time_delta, False)
                                if (track_event.type != previous_track_event) or (track_event.type == 0xFF):
                                    attempt.write(track_event.type.to_bytes(1, "big"))
                                if track_event.contents is not None:
                                    for k in track_event.contents:
                                        attempt.write(k.to_bytes(1, "big"))
                                if (track_event.type >= 0x90) and (track_event.type < 0xA0):
                                    length_duration_bytes = 0
                                    length_duration_bytes, duration = ReturnVLBytes(track_event.duration_time, length_duration_bytes)
                                    WriteVLBytes(attempt, duration, length_duration_bytes, False)
                                previous_track_event = track_event.type
                    for j in range(track_event_count[i]):
                        track_events[i][j].contents = None
    size_out = 0
    with open(out_file, "rb") as attempt:
        out_data = attempt.read()
        size_out = len(out_data)
        with open(temp_file, "wb") as temp:
            temp.write(out_data)
    offset_header = [None] * TRACK_LIMIT_SMALL
    extra_offsets = [0] * TRACK_LIMIT_SMALL
    with open(temp_file, "r+b") as temp:
        for i in range(TRACK_LIMIT_SMALL):
            offset_header[i] = int.from_bytes(temp.read(4), "big")
        for x in range(size_out):
            if x > 0x44:
                temp.seek(x)
                if int.from_bytes(temp.read(1), "big") == 0xFE:
                    for y in range(numberTracks):
                        if offset_header[y] > x:
                            extra_offsets[y] += 1
        with open(out_file, "wb") as attempt:
            for x in range(TRACK_LIMIT_SMALL):
                WriteLongToBuffer(temp, x*4, offset_header[x] + extra_offsets[x])
            for x in range(size_out):
                temp.seek(x)
                val = temp.read(1)
                attempt.write(val)
                if x > 0x44:
                    if val == 0xFE:
                        attempt.write(val)
    if no_repeaters:
        size_in = 0
        out_array = []
        output_spot = 0
        with open(out_file, "rb") as attempt:
            in_data = attempt.read()
            size_in = len(in_data)
            with open(temp_file, "wb") as temp:
                temp.write(in_data)
            with open(temp_file, "rb") as temp:
                offset = [None] * TRACK_LIMIT_SMALL
                for x in range(TRACK_LIMIT_SMALL):
                    offset[x] = int.from_bytes(temp.read(4), "big")
                quarter_note = int.from_bytes(temp.read(4), "big")
                out_array = [0] * (4 * size_in)
                offset_new = [0] * TRACK_LIMIT_SMALL
                output_spot = 0x44
                for x in range(TRACK_LIMIT_SMALL):
                    if offset[x] != 0:
                        offset_new[x] = output_spot
                        output_start = output_spot
                        end_spot = size_in
                        if x < 0xF:
                            if offset[x+1] != 0:
                                end_spot = offset[x+1]
                        y = offset[x]
                        while y < end_spot:
                            best_match_offset = -1
                            best_match_loop_count = -1
                            z = output_start
                            while z < output_spot:
                                match = 0
                                match_offset = 0
                                while True:
                                    temp.seek(y+match_offset)
                                    if out_array[z+match_offset] != int.from_bytes(temp.read(1), "big"):
                                        break
                                    if (y + match_offset) >= end_spot:
                                        break
                                    if out_array[z+match_offset] in (0xFE, 0xFF):
                                        break
                                    if z + match_offset >= output_spot:
                                        break
                                    seeAnFF = False
                                    checkFF = y+match_offset
                                    while (checkFF < end_spot) and (checkFF < (y+match_offset + 5)):
                                        temp.seek(checkFF)
                                        if int.from_bytes(temp.read(1), "big") == 0xFF:
                                            seeAnFF = True
                                        checkFF += 1
                                    if seeAnFF:
                                        break
                                    match_offset += 1
                                if (match_offset > best_match_loop_count) and (match_offset > 6):
                                    best_match_loop_count = match_offset
                                    best_match_offset = z
                                z += 1
                            loop_check = int((y - offset[x]) / 2)
                            if loop_check > 0xFD:
                                loop_check = 0xFD
                            if best_match_loop_count > 6:
                                if best_match_loop_count > 0xFD:
                                    best_match_loop_count = 0xFD
                                out_array[output_spot] = 0xFE
                                output_spot += 1
                                dist_back = (output_spot - best_match_offset) - 1
                                out_array[output_spot] = (dist_back >> 8) & 0xFF
                                out_array[output_spot + 1] = dist_back & 0xFF
                                out_array[output_spot + 2] = best_match_loop_count
                                output_spot += 3
                                y += best_match_loop_count
                            else:
                                temp.seek(y)
                                out_array[output_spot] = int.from_bytes(temp.read(1), "big")
                                output_spot += 1
                                y += 1
                    else:
                        break
                    if (output_spot % 4) != 0:
                        output_spot += (4 - (output_spot % 4))
                for x in range(TRACK_LIMIT_SMALL):
                    if offset_new[x] != 0:
                        output_start = offset_new[x]
                        end_spot = output_spot
                        if x < 0xF:
                            if offset_new[x+1] != 0:
                                end_spot = offset_new[x+1]
                        y = offset_new[x]
                        found_start = False
                        start_pos = 0
                        while y < end_spot:
                            if out_array[y] == 0xFF and out_array[y+1] == 0x2E and out_array[y+2] == 0 and out_array[y+3] == 0xFF:
                                found_start = True
                                start_pos = y + 4
                                y += 4
                            elif out_array[y] == 0xFF and out_array[y+1] == 0x2d and out_array[y+2] == 0xFF and out_array[y+3] == 0xFF:
                                if found_start:
                                    distance = (y + 8) - start_pos
                                    WriteLongToBuffer(out_array, y+4, distance)
                                    found_start = False
                                y += 8
                            else:
                                y += 1
                for x in range(TRACK_LIMIT_SMALL):
                    WriteLongToBuffer(out_array, x*4, offset_new[x])
                WriteLongToBuffer(out_array, 0x40, quarter_note)
        with open(out_file, "wb") as attempt:
            for x in range(output_spot):
                attempt.write(out_array[x].to_bytes(1, "big"))
    return True

repeaters = True # Should be True
success = MidiToGEFormat(midi_file, output_file, True, 3072, repeaters)
print("Successful", success)
with open(output_file, "r+b") as attempt:
    data_len = len(attempt.read())
    if data_len % 0x10 != 0:
        for x in range(0x10 - (data_len % 0x10)):
            attempt.write((0).to_bytes(1, "big"))
print(cmp(output_file, test_bin_file, shallow=False))