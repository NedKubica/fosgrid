# fosgrid

Python multi-threaded RTSP viewer with OpenCV decoding and dynamic resizing.

## Features
- live stream 1–4 RTSP cameras
- 4-camera 2×2 grid layout
- click any camera to toggle fullscreen
- press **F** to toggle fill / stretch mode
- 1 camera minimum

## Dependencies

Install required packages:

```
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-opencv python3-pil.imagetk
```

If needed:

```
pip3 install Pillow opencv-python
```

## Directions

### 1. Add 1–4 cameras to the config

Edit `config.json`:

```
[
  {
    "ip": "192.168.0.198",
    "port": 88,
    "username": "cam1",
    "password": "password",
    "path": "/videoMain"
  }
]
```

### 2. Make executable

```
chmod +x fosgrid.py
```

### 3. Run

```
./fosgrid.py
```

