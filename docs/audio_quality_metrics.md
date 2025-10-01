# Audio Quality Metrics Implementation

## Overview
This implementation adds comprehensive audio quality metrics to the Senda platform. All metrics are calculated automatically during audio generation and stored in a separate `audios` table with a one-to-one relationship to lessons.

## Database Schema

### Audio Table
New table with the following structure:

**Primary Fields:**
- `id`: UUID primary key
- `lesson_id`: Foreign key to lessons (unique)
- `url`: S3 URL of the audio file
- `file_size_mb`: File size in megabytes

**Duration Metrics:**
- `total_duration_seconds`: Actual audio duration
- `expected_duration_seconds`: Based on lesson.duration_minutes
- `duration_match_percentage`: How close actual matches expected

**Speech/Silence Metrics:**
- `speech_duration_seconds`: Total time with speech
- `silence_duration_seconds`: Total time of silence/pauses
- `speech_to_silence_ratio`: Ratio between speech and silence
- `speech_percentage`: Percentage of audio that is speech

**Silence Analysis:**
- `silence_segment_count`: Number of pause segments
- `longest_silence_seconds`: Duration of longest pause
- `average_silence_seconds`: Average pause duration

**Speech Analysis:**
- `speech_segment_count`: Number of detected speech segments
- `expected_speech_segment_count`: From script (for validation)

**Audio Quality:**
- `average_loudness_dbfs`: Average volume level
- `peak_loudness_dbfs`: Maximum volume level
- `dynamic_range_db`: Difference between peak and average

**Validation Flags:**
- `is_duration_valid`: Duration within acceptable range
- `is_speech_ratio_valid`: Speech percentage is appropriate
- `is_silence_gaps_valid`: No excessively long silences
- `is_segment_count_valid`: Speech segments match expectations
- `is_loudness_valid`: Volume levels are appropriate
- `is_file_size_valid`: File size matches expected for duration
- `is_quality_valid`: All validations pass

## Quality Thresholds

Defined in `AudioQualityThresholds` class:

```python
# Duration: within ±15% of expected
DURATION_TOLERANCE_PERCENTAGE = 15.0

# Speech ratio: 35-75% speech (meditation appropriate)
SPEECH_PERCENTAGE_MIN = 35.0
SPEECH_PERCENTAGE_MAX = 75.0

# Silence gaps: no single silence > 45 seconds
MAX_SINGLE_SILENCE_SECONDS = 45.0

# Segment count: within ±2 segments
SEGMENT_COUNT_TOLERANCE = 2

# Loudness: -40 to -10 dBFS average, peak > -6 dBFS
MIN_AVERAGE_LOUDNESS_DBFS = -40.0
MAX_AVERAGE_LOUDNESS_DBFS = -10.0
MIN_PEAK_LOUDNESS_DBFS = -6.0

# Dynamic range: 4-20 dB
MIN_DYNAMIC_RANGE_DB = 4.0
MAX_DYNAMIC_RANGE_DB = 20.0

# File size: 0.5-2.0 MB per minute
MIN_MB_PER_MINUTE = 0.5
MAX_MB_PER_MINUTE = 2.0
```

## Implementation Details

### Files Created
1. `src/senda/api/models/audio.py` - Audio model and thresholds
2. `src/senda/api/repositories/audio.py` - Audio repository
3. `src/senda/api/schemas/audio.py` - Pydantic schemas
4. `alembic/versions/f1a2b3c4d5e6_add_audio_table_with_quality_metrics.py` - Migration

### Files Modified
1. `src/senda/api/services/audio_service.py`:
   - Added `_calculate_audio_metrics()` method
   - Modified `generate_and_upload_lesson_audio()` to return tuple of (url, metrics)
   - Uses pydub's `detect_nonsilent()` for speech detection

2. `src/senda/api/models/lesson.py`:
   - Added `audio` relationship

3. `src/senda/api/routers/lesson.py`:
   - Updated audio generation task to save metrics
   - Added `GET /lessons/{lesson_id}/audio` endpoint

4. `src/senda/api/routers/course.py`:
   - Updated batch audio generation to save metrics

### Audio Metrics Calculation

The `_calculate_audio_metrics()` method:
1. Analyzes the generated AudioSegment object
2. Uses pydub's silence detection (-40 dBFS threshold)
3. Compares actual vs expected values from script
4. Calculates loudness using pydub's dBFS measurements
5. Validates each metric against thresholds
6. Returns dict with all metrics and validation flags

## API Usage

### Generate Audio (automatically calculates metrics)
```http
POST /api/lessons/{lesson_id}/generate-audio
```

### Get Audio Metrics
```http
GET /api/lessons/{lesson_id}/audio
```

**Response:**
```json
{
  "id": "uuid",
  "lesson_id": "uuid",
  "url": "https://s3.../audio.mp3",
  "file_size_mb": 9.2,
  "total_duration_seconds": 600.5,
  "expected_duration_seconds": 600.0,
  "duration_match_percentage": 100.08,
  "speech_duration_seconds": 380.2,
  "silence_duration_seconds": 220.3,
  "speech_to_silence_ratio": 1.73,
  "speech_percentage": 63.3,
  "silence_segment_count": 12,
  "longest_silence_seconds": 25.0,
  "average_silence_seconds": 18.4,
  "speech_segment_count": 13,
  "expected_speech_segment_count": 13,
  "average_loudness_dbfs": -23.5,
  "peak_loudness_dbfs": -8.2,
  "dynamic_range_db": 15.3,
  "is_duration_valid": true,
  "is_speech_ratio_valid": true,
  "is_silence_gaps_valid": true,
  "is_segment_count_valid": true,
  "is_loudness_valid": true,
  "is_file_size_valid": true,
  "is_quality_valid": true,
  "created_at": "2025-10-01T00:00:00Z"
}
```

## Migration Instructions

1. **Run the migration:**
   ```bash
   alembic upgrade head
   ```

2. **Verify table creation:**
   ```sql
   \d audios
   ```

3. **Note:** The migration removes `audio_url` and `audio_generated_at` columns from the `lessons` table. All new audio data will be stored in the `audios` table with comprehensive quality metrics.

## Monitoring Audio Quality

### Check for quality issues:
```sql
-- Find audios with any quality issues
SELECT l.title, a.url, 
       a.is_duration_valid, 
       a.is_speech_ratio_valid,
       a.is_silence_gaps_valid,
       a.is_quality_valid
FROM audios a
JOIN lessons l ON a.lesson_id = l.id
WHERE a.is_quality_valid = false;

-- Find audios with low speech percentage
SELECT l.title, a.speech_percentage, a.url
FROM audios a
JOIN lessons l ON a.lesson_id = l.id
WHERE a.speech_percentage < 40
ORDER BY a.speech_percentage;

-- Find audios with excessive silence gaps
SELECT l.title, a.longest_silence_seconds, a.url
FROM audios a
JOIN lessons l ON a.lesson_id = l.id
WHERE a.longest_silence_seconds > 30
ORDER BY a.longest_silence_seconds DESC;
```

## Future Enhancements

Potential additions:
1. **Spectral analysis**: Detect frequency issues or noise
2. **Pace detection**: Measure words per minute
3. **Consistency metrics**: Compare across lessons in a course
4. **Audio fingerprinting**: Detect duplicate or corrupted content
5. **Automated re-generation**: Trigger regeneration for failed quality checks
6. **Dashboard**: Visual analytics for audio quality trends

## Adjusting Thresholds

To modify thresholds, edit `AudioQualityThresholds` class in `src/senda/api/models/audio.py`:

```python
class AudioQualityThresholds:
    SPEECH_PERCENTAGE_MIN = 35.0  # Increase for more speech-heavy content
    MAX_SINGLE_SILENCE_SECONDS = 45.0  # Adjust for longer meditation pauses
    # ... etc
```

No migration needed - thresholds are applied at calculation time.
