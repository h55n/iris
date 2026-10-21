from iris.diarize import assign_speakers, merge_same_speaker

def test_assign_by_max_overlap():
    t = [{"start": 0, "end": 5, "text": "hi"}, {"start": 5.5, "end": 10, "text": "yo"}]
    d = [{"start": 0, "end": 4, "speaker": 0}, {"start": 4, "end": 10, "speaker": 1}]
    out = assign_speakers(t, d)
    assert out[0]["speaker"] == 0 and out[1]["speaker"] == 1

def test_segment_spanning_two_speakers_gets_majority():
    t = [{"start": 0, "end": 10, "text": "long"}]
    d = [{"start": 0, "end": 3, "speaker": 0}, {"start": 3, "end": 10, "speaker": 1}]
    assert assign_speakers(t, d)[0]["speaker"] == 1

def test_no_overlap_gives_none():
    t = [{"start": 20, "end": 25, "text": "x"}]
    d = [{"start": 0, "end": 5, "speaker": 0}]
    assert assign_speakers(t, d)[0]["speaker"] is None

def test_merge_same_speaker():
    d = [{"start": 0, "end": 2, "speaker": 0}, {"start": 2.5, "end": 4, "speaker": 0},
         {"start": 4.5, "end": 6, "speaker": 1}]
    m = merge_same_speaker(d)
    assert len(m) == 2 and m[0]["end"] == 4 and m[1]["speaker"] == 1

def test_merge_respects_gap():
    d = [{"start": 0, "end": 2, "speaker": 0}, {"start": 5, "end": 6, "speaker": 0}]
    assert len(merge_same_speaker(d)) == 2

def test_assign_speakers_empty_diarization_leaves_none():
    from iris import diarize as D
    out = D.assign_speakers([{"start": 0, "end": 5, "text": "hi"}], [])
    assert out[0]["speaker"] is None

def test_merge_empty_and_single():
    from iris import diarize as D
    assert D.merge_same_speaker([]) == []
    one = [{"speaker": 0, "start": 1.0, "end": 2.0}]
    assert D.merge_same_speaker(one) == one
