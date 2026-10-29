FROM python:3.12-slim

# ffmpeg with libass + a set of fonts covering the six FontFamily values (see reelcut/captions.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fontconfig \
        fonts-inter fonts-comic-neue fonts-liberation fonts-dejavu fonts-noto-color-emoji \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reelcut ./reelcut
# optional extra fonts (Anton, Bebas Neue, ...) -> mount or copy into /app/fonts and set REELCUT_FONTS_DIR
RUN mkdir -p /app/fonts /app/data
ENV REELCUT_WORK_DIR=/app/data REELCUT_FONTS_DIR=/app/fonts

EXPOSE 8000
CMD ["uvicorn", "reelcut.main:app", "--host", "0.0.0.0", "--port", "8000"]
