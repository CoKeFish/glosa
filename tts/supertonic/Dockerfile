# Supertonic 3 (Supertone): small ONNX text-to-speech, CPU only, 31 languages.
# Serves an OpenAI-compatible /v1/audio/speech on port 7788. The model downloads on
# first start into the mounted cache volume.
FROM python:3.12-slim

RUN pip install --no-cache-dir "supertonic[serve]"

EXPOSE 7788
CMD ["supertonic", "serve", "--host", "0.0.0.0", "--port", "7788"]
