from music21 import *
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
import numpy as np
from music.matrix import MusicMatrixRepresentation
from music.processor import get_musicxml_from_music21, get_music21_from_music_matrix_representation
import math

# TODO: clean up structure
def get_all_exercises(score):
        # turn l into a hashmap
        l = defaultdict(list)

        exerciseScore = ExerciseScore(score)

        # if the score has multiple lines, we want to display the entire score together, otherwise we don't display score-level since it's the same as part-level
        # if len(exerciseScore.parts) > 1:
        description = "Full excerpt view with all parts together, unaltered.<br><br>Purpose: To isolate and target practice the selected measure(s)."
        l['Score Level'].append((description, get_musicxml_from_music21(exerciseScore.original_stream)))
        # else:
        #     l['Score Level'].append((None, None))

        for part in exerciseScore.parts:
            # if the part has multiple lines, we want to display the entire part together, otherwise we don't display part-level since it's the same as line-level
            # if len(part.lines) > 1:
            # if len(exerciseScore.parts) > 1:
            description = "Complete part view, showing all voices per part.<br><br>Purpose: To isolate and target practice one part at a time."
            l['Part Level'].append((description, get_musicxml_from_music21(part.original_stream)))
            # else:
                # l['Part Level'].append((None, None))
            
            for line in part.lines:
                description = "Single voice view, showing all notes in a single voice or melodic line.<br><br>Purpose: To isolate and target practice one voice at a time."
                # if len(part.lines) > 1:
                l['Voice Level: original'].append((description, get_musicxml_from_music21(line.original_stream)))
                for exercise_name, exercises in line.exercises.items():
                    # l['line_generated_exercise'].append(get_musicxml_from_music21(exercise))
                    for exercise in exercises:
                        # improve the descriptions + tooltip
                        description = f"{exercise_name.replace('_', ' ').title()} exercise.<br><br>Purpose: [details on why insert here]"
                        l["Voice Level: " + exercise_name.replace('_', ' ').title()].append((description, get_musicxml_from_music21(exercise)))
        return l

class Score:
    def __init__(self, filename):
        self.filename = filename
        self.score_mxl = converter.parse(filename)
        self.exercises = get_all_exercises(self.score_mxl)
        # self.bpm = 

    def get_exercises(self):
        return self.exercises

    def get_score_mxl(self):
        return self.score_mxl

# TODO: change name to make more sense
class MusicMatrixRepresentation:
    def __init__(self, key_signature, time_signature, quantization, piano_roll, onset_map, durations_matrix):
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization
        self.piano_roll = piano_roll
        self.onset_map = onset_map
        self.durations_matrix = durations_matrix

class ExerciseScore:
    def __init__(self, music21_score):
        self.original_stream = music21_score

        key_signatures = self.original_stream.recurse().getElementsByClass(key.KeySignature)
        self.key_signature = key_signatures[0] if key_signatures else None
        self.time_signature = self._extract_time_signature() # music21 time signature object
        self.quantization = self._calculate_quantization() # int

        self.parts = self._extract_parts() # list of ExercisePart objects
    
    def _extract_time_signature(self):
        """
        Extract the time signature from the music21 line.
        Currently only supports one time signature per line. 

        # TODO: handle multiple time signatures
        """
        time_signature = self.original_stream.recurse().getElementsByClass(meter.TimeSignature)
        if time_signature:
            return time_signature[0]
        else:
            return None

    # TODO: need to consider if there isn't a time signature
    def _calculate_quantization(self):
        """
        Calculate the quantization based on the time signature and the shortest note value in the excerpt.
        """
        durations = [
            n.duration.quarterLength
            for n in self.original_stream.recurse().notesAndRests
            if n.duration.quarterLength > 0
        ]

        if not durations:
            return None
    
        shortest = min(durations)
        quantization = math.ceil(1 / shortest)

        return quantization * self.time_signature.numerator

    def _extract_parts(self):
        """
        Create and return a list of ExercisePart objects from the score (music21 stream notation).
        """

        # TODO: if the part doesn't have notes, don't process it
        # return [ExercisePart(part, self.key_signature, self.time_signature, self.quantization) for part in self.original_stream.parts if part not None]
        parts = []
        for part in self.original_stream.parts:
            if part.recurse(classFilter=('Note', 'Chord')):
                parts.append(ExercisePart(part, self.key_signature, self.time_signature, self.quantization))
        return parts

class ExercisePart():
    def __init__(self, music21_part, key_signature, time_signature, quantization):
        self.original_stream = music21_part
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization
        self.lines = self._extract_lines() # list of ExerciseLine objects
    
    def _extract_lines(self):
        # this extracts the voices from the parts
        split_voices = self.original_stream.voicesToParts()
        lines = []
        for line in split_voices.parts:
            if line.recurse(classFilter=('Note', 'Chord')):
                lines.append(ExerciseLine(line, self.key_signature, self.time_signature, self.quantization))
        return lines
        # TODO: also get rid of parts with no notes in it

# TODO: change this name to "Voice" instead of "Line"?????
class ExerciseLine:
    def __init__(self, music21_line, key_signature, time_signature, quantization):
        self.original_stream = music21_line  # music21 stream object
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization

        # might have to move some functions around and whatever but keep like this for now
        piano_roll, onset_map, durations_matrix = self._create_matrices() # numpy arrays

        self.music_matrix_representation = MusicMatrixRepresentation(
            key_signature = key_signature,
            time_signature=time_signature,
            quantization=quantization,
            piano_roll=piano_roll,
            onset_map=onset_map,
            durations_matrix=durations_matrix
        )

        self.exercises = self.generate_exercises() # map of exercise name to music21 stream object

    def _create_matrices(self):
        # Get the measure offsets
        measure_offset = {}
        for el in self.original_stream.recurse(classFilter=('Measure')):
            measure_offset[el.measureNumber] = el.offset
        
        # Get the duration of the part
        duration_max = 0
        for el in self.original_stream.recurse(classFilter=('Note', 'Chord')):
            t_end = self._get_end_time(el,measure_offset,self.quantization)
            if(t_end>=duration_max):
                duration_max=t_end

        # Get the pitch and offset+duration
        piano_roll = np.zeros((128,math.ceil(duration_max)))

        # TODO: handle / account for the ties
        onset_map = np.zeros((128,math.ceil(duration_max)))

        durations_matrix = np.zeros((128,math.ceil(duration_max)))
        if duration_max == 0: 
            return piano_roll, onset_map, durations_matrix
        
        for el in self.original_stream.recurse(classFilter=('Note', 'Chord')):
            note_start = self._get_start_time(el,measure_offset,self.quantization)
            note_end = self._get_end_time(el,measure_offset,self.quantization)

            if el.isChord:
                for pitch in el.pitches:
                    midi = pitch.midi
                    onset_map[midi, note_start] = 1
                    piano_roll[midi, note_start:note_end] = 1
            else:
                midi = el.pitch.midi
                if el.tie != tie.Tie('stop'):
                    onset_map[midi, note_start] = 1
                piano_roll[midi,note_start:note_end] = 1

        rows, cols = piano_roll.shape

        for i in range(rows):
            onset_indices = np.where(onset_map[i] == 1)[0]
            for idx, start in enumerate(onset_indices):
                end = onset_indices[idx + 1] if idx + 1 < len(onset_indices) else cols
                # Sum the 1s in the piano roll between onset and next onset or end of row
                duration = np.sum(piano_roll[i, start:end])
                durations_matrix[i, start] = duration

        # plot_mtx(piano_roll)
        
        return piano_roll, onset_map, durations_matrix

    def _get_start_time(self, el,measure_offset,quantization):
        if (el.offset is not None) and (el.measureNumber in measure_offset):
            return int(math.ceil((measure_offset[el.measureNumber] + el.offset)*quantization))
        return None

    def _get_end_time(self, el,measure_offset,quantization):
        if (el.offset is not None) and (el.measureNumber in measure_offset):
            return int(math.ceil((measure_offset[el.measureNumber] + el.offset + el.duration.quarterLength)*quantization))
        return None

    def generate_exercises(self):
        """
        Generate exercises from the music matrix representation. Exercises are returned as music21 streams.
        """
        # exercises = []
        exercises = defaultdict(list)

        # try:

        # generated dotted exercises
        dotted_duration_patterns = [[1.5, 0.5], [0.5, 1.5]]
        for pattern in dotted_duration_patterns:
            dotted = self.generate_dotted_exercise(pattern)
            
            # exercises.append(dotted)
            exercises['dotted'].append(dotted)

        # generate the chord exercise
        # maybe just have this be all multiples of the numerator or denominator ranging from min quantization level to bar level? TODO
        level_of_chordification = set([self.music_matrix_representation.quantization, self.music_matrix_representation.quantization * 2, self.music_matrix_representation.quantization // 2, self.music_matrix_representation.time_signature.denominator, self.music_matrix_representation.time_signature.denominator * 2, self.music_matrix_representation.time_signature.denominator // 2, self.music_matrix_representation.time_signature.numerator * self.music_matrix_representation.time_signature.denominator])
        for chord_level in level_of_chordification:
            chordify = self.generate_chordify_exercise(chord_level)
            if chordify is not None:
                exercises['chordified'].append(chordify)

        # generate slowed down exercises
        factor_of_slowdown = [2, 4] # i.e., 2 is twice as slow, 4 is four times as slow
        for factor in factor_of_slowdown:
            slowed_down = self.generate_slowed_down_exercise(factor)
            if slowed_down is not None:
                exercises['slowed_down'].append(slowed_down)

        return exercises
    
    def generate_dotted_exercise(self, dotted_duration_pattern):
        """
        Generate a dotted exercise from the music matrix representation.
        """
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        # 2. find the ranges where there is an even pattern to dottify
        ranges = self._find_duplicate_length_ranges(flattened_durations_list)

        # 3. iterate through the given duration list and modify the rhythm durations in the flattened duration list
        dotted_flat_durations = flattened_durations_list.copy()
        n = len(dotted_duration_pattern)

        # only works if durations are integers
        for start_time, end_time, num_notes in ranges: # [(0, 8, 4)]
            dotted_factor_i = 0

            old_rhythm_phrase = flattened_durations_list[start_time:end_time]
            new_rhythm_phrase = [0] * (end_time - start_time)

            # [2,0,2,0,2,0,2,0]
            # [3,0,0,1,3,0,0,1]
            old_rhythm_i = 0
            t = start_time
            new_rhythm_i = 0
            while t < end_time and new_rhythm_i < len(new_rhythm_phrase) and old_rhythm_i < len(old_rhythm_phrase):
                old_duration = old_rhythm_phrase[old_rhythm_i]
                new_dur = old_duration * dotted_duration_pattern[dotted_factor_i]
                if new_dur <= 0:
                    print("Invalid duration, skipping...")
                    break
                new_dur = int(new_dur)
                new_rhythm_phrase[new_rhythm_i] = new_dur

                # update hashmap of time to pitches
                pitches_to_update = pitches_hashmap[start_time + old_rhythm_i]
                pitches_hashmap[start_time + old_rhythm_i] = []
                pitches_hashmap[t] = pitches_to_update
                
                old_rhythm_i += old_duration
                dotted_factor_i = (dotted_factor_i + 1) % n
                new_rhythm_i += new_dur
                t += new_dur
                
            dotted_flat_durations[start_time:end_time] = new_rhythm_phrase

        # 4. update the piano roll and onset map to reflect the flattened durations (maybe can do one pass, but splitting them for now)

        # 4.0. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros_like(self.music_matrix_representation.durations_matrix)
        for time, pitches in pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = dotted_flat_durations[time]

        # 4.1. update the onset map by copying and boolean-ifying the unflatted duration
        dotted_onset_map = new_durations_matrix.copy()
        mask = dotted_onset_map != 0
        dotted_onset_map[mask] = 1

        # 4.2. update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=dotted_onset_map,
            durations_matrix=new_durations_matrix
        ))
    

    # TODO: beats are weird for three blind mice first measure? extra eighth note
    def generate_chordify_exercise(self, chord_level):
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        # 2. find the ranges where there is an even pattern to dottify
        ranges = self._find_duplicate_length_ranges(flattened_durations_list)

        chordified_flat_durations = flattened_durations_list.copy()

        # 3. the range will give ALL notes similar in rhythm, iterate through the ranges and group them into X total chords based on quantization and feasibility of actually being played (so 4-5 notes max, and an interval difference no greater than an octave), and update the MMR info
        for start_time, end_time, num_notes in ranges:
            # get the groupings of notes to make into chords via times
            sub_groupings = self._find_sub_groupings(flattened_durations_list, start_time, end_time, chord_level)

            # for each sub-grouping, turn the mini-grouping into a chord by modifying the piano roll, onset map, and durations matrix to turn all the 1s in the earliest to latest time into 1s, onset at the earliest time for each affected pitch, and duration for all affected pitches to be the last time - earliest time
            for sub_start_time, sub_end_time in sub_groupings:
                
                total_duration = sum(flattened_durations_list[sub_start_time:sub_end_time])
                new_rhythm_phrase = [0] * (sub_end_time - sub_start_time)
                new_rhythm_phrase[0] = total_duration

                chordified_flat_durations[sub_start_time:sub_end_time] = new_rhythm_phrase

                # get the indices of the non-zero durations in the sub-grouping
                # update the hashmap of time to pitches
                non_zero_indices = [i for i in range(sub_start_time, sub_end_time-1) if flattened_durations_list[i] != 0]
                pitches = set()

                for i in non_zero_indices:
                    c_pitches = pitches_hashmap[i]
                    for p in c_pitches:
                        pitches.add(p)

                # if the distance in pitches is greater than an octave, skip this sub-grouping
                if pitches and max(pitches) - min(pitches) > 12:
                    return None

                # too many notes to chord, skip this sub-grouping
                if len(non_zero_indices) > 5:
                    return None

                for i in non_zero_indices:
                    pitches_to_update = pitches_hashmap[i]
                    pitches_hashmap[i] = []
                    pitches_hashmap[sub_start_time].append(pitches_to_update)

        # if new flat duration is the same as the old one, return None
        if flattened_durations_list == chordified_flat_durations:
            return None

        # 4. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros_like(self.music_matrix_representation.durations_matrix)
        for time, pitches in pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = chordified_flat_durations[time]
        
        # update the onset map by copying and boolean-ifying the unflatted duration
        chordified_onset_map = new_durations_matrix.copy()
        mask = chordified_onset_map != 0
        chordified_onset_map[mask] = 1

        # update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=chordified_onset_map,
            durations_matrix=new_durations_matrix
        ))


    def generate_slowed_down_exercise(self, factor):
        """
        Generate a slowed down exercise from the music matrix representation.
        """
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        # slow down the entire flattened durations list by the factor, meaning we multiply the durations by the factor
        # flattened durations list has to be len * factor as long
        new_durations_list = [0] * (len(flattened_durations_list) * factor)
        for i in range(len(flattened_durations_list)):
            new_durations_list[i * factor] = flattened_durations_list[i] * factor

        # update the hashmap of time to pitches
        new_pitches_hashmap = defaultdict(list)
        items = list(pitches_hashmap.items())
        for time, pitches in items:
            for p in pitches:
                new_pitches_hashmap[time * factor].append(p)

        # if new flat duration is the same as the old one, return None
        if flattened_durations_list == new_durations_list:
            return None

        # 4. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros((128, len(new_durations_list)))
        for time, pitches in new_pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = new_durations_list[time]
        
        # update the onset map by copying and boolean-ifying the unflatted duration
        chordified_onset_map = new_durations_matrix.copy()
        mask = chordified_onset_map != 0
        chordified_onset_map[mask] = 1

        # update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=chordified_onset_map,
            durations_matrix=new_durations_matrix
        ))


    def _find_sub_groupings(self, flattened_durations_list, start_time, end_time, chord_level):
        # TODO: improve on this, but currently split the group by the time signature denominator
        sub_groupings = []
        for i in range(start_time, end_time, chord_level):
            sub_groupings.append((i, min(i + chord_level, end_time)))

        return sub_groupings

    
    def _flatten_durations(self):
        flat = [int(x) for x in self.music_matrix_representation.durations_matrix[0]]

        # time_index : [midi pitch 1, midi pitch 2]
        hashmap = defaultdict(list)

        for ri, ci in np.ndindex(self.music_matrix_representation.durations_matrix.shape):
            if self.music_matrix_representation.durations_matrix[ri, ci] != 0:
                if flat[ci] == 0:
                    flat[ci] = int(self.music_matrix_representation.durations_matrix[ri, ci])
                hashmap[ci].append(ri)

        return flat, hashmap
    
    def _find_duplicate_length_ranges(self, durations_list):
        windows = [] # start_time, end_time
        
        curr_val_count = 0
        curr_val = -1
        i = 0
        j = 0
        # for j in range(len(durations_list)):
        while j < len(durations_list):
            if durations_list[j] > 0:
                if curr_val < 0:
                    curr_val = durations_list[j]
                    curr_val_count += 1
                    i = j
                elif durations_list[j] == curr_val:
                    curr_val_count += 1
                else:
                    if curr_val_count > 1:
                        windows.append((i, j, curr_val_count))
                    curr_val = durations_list[j]
                    curr_val_count = 1
                    i = j

            j += 1

        if curr_val_count > 1:
            windows.append((i, j, curr_val_count))

        return windows

    def _reconstruct_piano_roll(self, durations_matrix):
        new_piano_roll = np.zeros_like(durations_matrix)

        rows, cols = durations_matrix.shape

        for r in range(rows):
            row = durations_matrix[r]

            c = 0
            while c < cols:
                dur = int(durations_matrix[r, c])
                if dur == 0:
                    c += 1
                else:
                    x = c
                    for dx in range(dur):
                        # NOTE: THIS IS A TEMPORARY SOLUTION, DOES NOT FULLY SOLVE THE DOTTED RHYTHM NEEDING RESTS ISSUE? need to fix the durations matrix to account for rests
                        if (x+dx) >= cols:
                            break
                        new_piano_roll[r, x+dx] = 1
                    c += dur

        return new_piano_roll
