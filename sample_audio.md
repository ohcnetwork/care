# Sample Audio File

This is a placeholder for the sample audio file.

## Instructions

Replace the `sample_audio.mp3` file with an actual audio recording for testing.

### Supported Formats
- mp3
- mp4
- m4a
- wav
- webm
- flac
- ogg
- oga
- mpeg
- mpga

### Requirements
- Maximum file size: 25MB
- Should contain medical consultation audio for best results

### Example Audio Content
The audio should contain a medical consultation, for example:
- Doctor-patient conversation
- Symptom discussion
- Medical history review
- Diagnosis and treatment discussion

### Quick Test with Text-to-Speech

If you don't have a real audio file, you can create a test one using macOS's say command:

```bash
say -o sample_audio.aiff "Doctor: Good morning, how are you feeling today? Patient: I have been having headaches for the past week. Doctor: Can you describe the pain? Patient: It is a throbbing pain on the right side of my head. Doctor: Any nausea or sensitivity to light? Patient: Yes, bright lights make it worse. Doctor: Based on your symptoms, this sounds like a migraine. I am prescribing Sumatriptan 50mg to take when you feel the headache coming on."

# Convert to mp3 (requires ffmpeg)
ffmpeg -i sample_audio.aiff sample_audio.mp3
rm sample_audio.aiff
```

Or on Linux with espeak and ffmpeg:

```bash
espeak "Doctor: Good morning, how are you feeling today?" -w sample_audio.wav
ffmpeg -i sample_audio.wav sample_audio.mp3
```
