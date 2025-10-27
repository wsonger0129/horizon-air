# 🌄 HorizonAir
By Andrew Muntek To, Maxwell Hsieh, and Whitney Songer<br>University of California, Irvine — Computer Engineering Senior Design Project

## 📘 Overview

HorizonAir is an AI-driven drone platform designed for hikers and outdoor explorers. The system autonomously scans surrounding environments to identify scenic areas such as viewpoints, clearings, and water features, and then uses an iPhone application to guide users safely toward these areas through augmented reality (AR) overlays.

By combining LiDAR, camera imaging, and machine learning, HorizonAir creates a real-time understanding of terrain and visual appeal — offering explorers a new way to discover beautiful landscapes safely and intelligently.

## 🚀 Key Features
🧠 AI Scenic Detection
- Uses lightweight machine learning models to detect visually “scenic” environments (e.g., wide vistas, lakes, cliffs).
- Trained on curated terrain and viewpoint datasets.
- Inference runs on the user’s iPhone via CoreML, minimizing onboard compute requirements.

🌐 ARKit Integration
- Apple’s ARKit framework visualizes detected scenic locations directly in the real world.
- Users see AR navigation arrows and overlays indicating the direction and distance to the identified area.
- Ensures FAA line-of-sight compliance by only operating within visible range.

🛰️ LiDAR + Vision Fusion
- LiDAR data improves environmental understanding (depth, terrain mapping).
- Combined with RGB imagery to identify both aesthetic value and navigational safety.

📱 iPhone Application
- Real-time drone telemetry and map view.
- Augmented Reality (AR) navigation overlay for safe pathfinding.
- Offline operation capability (no cloud dependency).

⚙️ Hardware Platform
- Base drone kit with modular frame and brushless motors.
- LiDAR and camera modules mounted on gimbal for terrain scanning.
- Raspberry Pi Zero 2 W for onboard preprocessing (compression, telemetry).
- ExpressLRS for long-range control and telemetry.
- 5.8 GHz FPV transmitter for short-range video streaming.

## 🏗️ System Architecture
**Drone (Edge Device)**
- Captures LiDAR + camera data.
- Performs lightweight preprocessing (compression + downsampling).
- Transmits frames and telemetry over Wi-Fi to iPhone.
**iPhone (Ground Station)**
- Runs CoreML scenic detection model.
- Uses ARKit for scene visualization and navigation.
- Displays detected scenic areas and suggested paths.
**No Cloud Needed:**
All AI inference and AR rendering occur locally on the iPhone for low latency and offline reliability.


## 🧩 Technologies Used
**Hardware**
- Raspberry Pi Zero 2 W
- LiDAR module
- 5MP camera module (OV5647 sensor)
- MATEK F405 Flight Controller
- XING2 Brushless Motors
- ExpressLRS receiver + 5.8 GHz FPV transmitter<br>
**Software**
- Python / C++ (Drone Control + Data Processing)
- Swift + ARKit + CoreML (iOS App)
- TensorFlow / PyTorch (Model Training)
- OpenCV (Vision Preprocessing)
- UART / Wi-Fi / ELRS (Communication Protocols)

## ⚖️ FAA Compliance
HorizonAir operates strictly within visual line-of-sight (VLOS) guidelines. The system’s app includes geofencing and altitude-limiting features to ensure compliance with Part 107 hobbyist and educational drone regulations.

## 🎯 Project Goals
1. Innovation: merge AI, LiDAR, and AR for outdoor exploration.
2. Accessibility: provide intuitive, visual guidance for hikers of all skill levels.
3. Feasibility: demonstrate a real-time, on-device system within a 20-week academic schedule.
4. Scalability: design for future extensions (crowdsourced scenic map, environmental hazard alerts, etc.).

## 🧭 Future Directions
- Multi-drone cooperative mapping of large scenic regions.
- Integration with Apple’s Vision Pro for immersive AR exploration.
- Cloud-based scenic database for global user sharing.
- AI expansion to include wildlife, vegetation, or environmental feature recognition.

## 📸 Project Media
To be added:
- System architecture diagram
- App interface mockups
- Drone setup photos
- Demo video link

## 📜 License
This project is for educational and research purposes under the University of California, Irvine Senior Design Program.