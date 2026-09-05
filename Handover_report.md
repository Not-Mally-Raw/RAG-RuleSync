# FaceVault — Project Handover Report
### Custom Face Detection & Recognition Engine | Technical & Stakeholder Reference

---

> **Document Purpose:** This report serves as a complete handover document for both the incoming development team and project stakeholders. It covers system architecture, the ML training pipeline, deployment setup, known issues with recommended fixes, and a comparative analysis of the technology choices made. The system is delivered as a **reusable recognition engine and ML artifact**, not a fixed deployment product.

---

## Table of Contents

1. [Project Overview & Scope](#1-project-overview--scope)
2. [System Architecture](#2-system-architecture)
3. [ML Pipeline — Training & Model Details](#3-ml-pipeline--training--model-details)
4. [Backend API Reference](#4-backend-api-reference)
5. [Frontend Dashboard](#5-frontend-dashboard)
6. [Vector Database — Pinecone Setup](#6-vector-database--pinecone-setup)
7. [Deployment & Environment Setup](#7-deployment--environment-setup)
8. [Known Issues & Critical Bugs](#8-known-issues--critical-bugs)
9. [Technology Comparison & Alternatives](#9-technology-comparison--alternatives)
10. [Future Work & Roadmap](#10-future-work--roadmap)
11. [Glossary](#11-glossary)

---

## 1. Project Overview & Scope

### What FaceVault Is

FaceVault is a **custom-trained face detection and recognition engine** built around a curated 35,000-image dataset. It provides a complete pipeline from raw image or video input to a verified identity result, exposed via a REST API and a browser-based management dashboard.

The core deliverable of this project is:

- A **custom YOLOv8n face detection model** trained from scratch on a curated dataset
- A **FaceNet-based 512-dimensional embedding pipeline** for identity representation
- A **Pinecone-backed cosine similarity matching system** for real-time identity lookup
- A **Flask REST API** to expose all capabilities to client applications
- A **frontend dashboard** for enrollment, monitoring, and media processing

### What FaceVault Is NOT

This project is scoped as a **model and inference pipeline**. It explicitly does not cover:

- Large-scale CCTV infrastructure or camera installation
- Multi-camera synchronization or cross-camera tracking
- Edge device deployment or embedded hardware optimization
- Surveillance application buildout for any specific organization

> **For Stakeholders:** The recognition engine is designed to be modular. Once integrated by a downstream engineering team, it can serve as the core component in attendance systems, access control, event media indexing, or similar applications.

### Inference Pipeline (End-to-End)

```
Full Image / Video Frame
         │
         ▼
  ┌─────────────────┐
  │  YOLOv8n Model  │  ← Custom-trained face detector
  │  (Detection)    │    Outputs: bounding boxes + confidence scores
  └────────┬────────┘
           │  Crop face regions
           ▼
  ┌─────────────────┐
  │    FaceNet      │  ← InceptionResnetV1 (vggface2 pretrained)
  │  (Embedding)    │    Outputs: 512-dimensional embedding vector
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │    Pinecone     │  ← Cosine similarity search
  │ (Vector Search) │    Index: face-recognition-index
  └────────┬────────┘
           │
           ▼
   Identity Result
   (Name + Confidence Score + Bounding Box)
```

---

## 2. System Architecture

FaceVault follows a standard three-tier client-server architecture with an additional external vector database layer.

```
┌──────────────────────────────────────────────────┐
│               CLIENT LAYER                        │
│   face_recognition_advanced.html                 │
│   Vanilla JS · CSS Variables · FontAwesome       │
└─────────────────────┬────────────────────────────┘
                      │ HTTP (Fetch API)
                      ▼
┌──────────────────────────────────────────────────┐
│               API LAYER                           │
│   app.py  (Flask + Flask-CORS)                   │
│   Handles routing, file I/O, request validation  │
└─────────────────────┬────────────────────────────┘
                      │ Python method calls
                      ▼
┌──────────────────────────────────────────────────┐
│            ML PIPELINE LAYER                      │
│   model3.py                                      │
│   YOLOv8n → FaceNet → Embedding generation      │
│   GPU-accelerated via PyTorch + CUDA            │
└─────────────────────┬────────────────────────────┘
                      │ Pinecone Python Client
                      ▼
┌──────────────────────────────────────────────────┐
│           VECTOR DATABASE LAYER                   │
│   Pinecone Serverless (AWS us-east-1)            │
│   Index: face-recognition-index                  │
│   Metric: Cosine Similarity · Dimensions: 512   │
└──────────────────────────────────────────────────┘
```

### File Structure

```
FaceVault/
├── app.py                        # Flask API server
├── model3.py                     # ML pipeline (YOLO + FaceNet + Pinecone)
├── face_recognition_advanced.html # Frontend dashboard
├── requirements.txt              # Python dependencies
├── uploads/                      # Incoming user files (auto-created)
├── outputs/                      # Processed/annotated output files
└── static/                       # Enrolled face images served to frontend
```

---

## 3. ML Pipeline — Training & Model Details

> **Traceability Note:** The training, evaluation scripts, and validation dataset splits are tracked separately in the accompanying `Face_Recognition_Evaluation_Metrics 2.ipynb` notebook artifact. This notebook serves as the reproducible source of truth and proof of the metrics cited below.

### 3.1 Dataset

| Property | Details |
|---|---|
| Total Images | ~35,000 |
| Curation Method | Manually curated |
| Coverage | Multiple lighting conditions, angles, and expressions |
| Preprocessing | Noise filtering, normalization, quality thresholding |
| Augmentation | Applied during training (flips, brightness shifts, rotation) |
| Task | Face detection (bounding box localization) |

The dataset is the **primary research contribution** of this project. Existing public datasets were either access-restricted, low-quality, or domain-mismatched. Curating a custom 35K dataset ensures control over quality variance and labeling accuracy, which directly improves downstream embedding reliability.

### 3.2 Face Detection Model — YOLOv8n

| Property | Details |
|---|---|
| Architecture | YOLOv8n (nano — optimized for speed) |
| Framework | Ultralytics |
| Task | Object detection (face localization) |
| Input | Full resolution image or video frame |
| Output | Bounding boxes + confidence scores |
| Post-processing | Non-Maximum Suppression (NMS) + confidence thresholding |
| Weights File | `Face_Detect_last.pt` |
| Fallback | OpenCV Haar Cascades (if YOLO fails to load) |

**Why YOLOv8n specifically:** The nano variant was chosen to balance inference speed with detection accuracy for real-time video processing. It runs efficiently on GPU (CUDA) and degrades gracefully to CPU if no GPU is available. As proven in the evaluation artifact, inference logic is highly optimized (approx. 3.7 ms per image at 154 FPS).

### 3.3 Feature Extraction Model — FaceNet

| Property | Details |
|---|---|
| Architecture | InceptionResnetV1 |
| Pretrained On | VGGFace2 |
| Library | `facenet-pytorch` |
| Input | Cropped face region, resized to 160×160px |
| Output | 512-dimensional embedding vector |
| Normalization | Standard ImageNet-style normalization applied pre-inference |

**What the embedding represents:** Each face is converted into a point in 512-dimensional space. Faces belonging to the same person cluster close together under cosine similarity. Faces of different people are far apart. This allows identity verification without storing raw images in the database. 

> **Note on `requirements.txt`:** The requirements file references DINOv3 as a dependency. This is a **legacy artifact** from an earlier experimental phase. The active codebase uses FaceNet exclusively. DINOv3 is not used anywhere in `model3.py` and can be safely removed from requirements.

### 3.4 Performance Metrics

The following metrics were achieved during the end-to-end pipeline evaluation script using the YOLOv8n detector coupled with FaceNet embeddings and Cosine similarity (threshold 0.55):

#### Detection Metrics (YOLOv8n)
| Metric | Result |
|---|---|
| Precision | 0.9681 |
| Recall | 0.9256 |
| F1 Score | 0.9464 |
| mAP@0.5 | 0.9572 |
| mAP@0.5:0.95 | 0.7630 |
| Mean IoU | 0.8580 |
| Inference Speed | 154.1 FPS (3.7 ms/img) |

#### Full Pipeline Accuracy
| Metric | Result |
|---|---|
| Detection Rate | 100.00% |
| Overall Recognition Accuracy | 100.00% |
| Accuracy (given detection) | 100.00% |
| Batch Pipeline Latency | 31.0 ms avg (32.3 FPS) |
| Latency Breakdown | Detect: ~11ms, Embed: ~19ms, Match: ~0.1ms |

### 3.5 Multi-Angle Enrollment Strategy

For users enrolled with multiple images (bulk enrollment), the system applies an **adaptive multi-angle scoring strategy**:

- Up to 10 images per identity can be enrolled
- Each image generates its own 512D embedding, stored separately in Pinecone
- At query time, the system retrieves the top-K matches across all vectors for a given identity
- A **confidence boost** is applied to identities with multi-angle coverage, reducing false negatives from varied poses or lighting

This is particularly valuable in uncontrolled environments where a person's face angle cannot be guaranteed.

### 3.6 GPU Optimization

- CUDA is used automatically when available via `torch.cuda.is_available()`
- A **dummy tensor warm-up pass** is executed at initialization to pre-allocate GPU memory, ensuring the first real inference request is not penalized by CUDA initialization latency
- Video processing supports configurable **frame skipping** and **resolution downscaling** across three quality modes:

| Mode | Frame Skip | Resolution Scale | Use Case |
|---|---|---|---|
| Fast | High | Reduced | Long videos, speed priority |
| Balanced | Medium | Medium | General use |
| Maximum Quality | None | Full | Short clips, accuracy priority |

---

## 4. Backend API Reference

**Base URL:** `http://127.0.0.1:5000`

### Endpoints

#### `POST /api/enroll`
Enroll a single face into the database.

- **Body:** `multipart/form-data` — `image` (file), `name` (string)
- **Response:** `{ success, message, face_id, embedding_preview }`
- **Notes:** Extracts face, computes 512D embedding, upserts to Pinecone with name metadata.

---

#### `POST /api/bulk-enroll`
Enroll multiple images of the same person for improved accuracy.

- **Body:** `multipart/form-data` — `images[]` (up to 10 files), `name` (string)
- **Response:** `{ success, enrolled_count, failed_count, details[] }`
- **Notes:** Each image creates a separate vector in Pinecone. Multi-angle scoring is automatically applied at recognition time.

---

#### `POST /api/process`
Process an image or video for face recognition.

- **Body:** `multipart/form-data` — `file` (image or video), `mode` (fast | balanced | maximum)
- **Response:** `{ success, output_path, faces_detected, identities[], processing_time }`
- **Notes:** Returns annotated media with bounding boxes and identity labels drawn.

---

#### `GET /api/faces`
Retrieve all enrolled faces and metadata.

- **Response:** `{ faces: [{ id, name, image_path, enrollment_type, quality_score }] }`

---

#### `POST /api/camera/start`
Start real-time webcam recognition stream.

- **Response:** `{ success, message }`
- **Known Issue:** Uses global state — only one concurrent camera session is supported. See Section 8.

---

#### `POST /api/camera/stop`
Stop the active camera stream.

- **Response:** `{ success, message }`

---

#### `POST /api/convert-video`
Convert video to browser-compatible format using FFmpeg.

- **Body:** `multipart/form-data` — `file`
- **Response:** `{ success, output_path }`
- **Known Issue:** Silent failure if FFmpeg is not installed. See Section 8.

---

#### `GET /api/health`
System health check — GPU memory, model load status, Pinecone connection.

- **Response:** `{ gpu_available, gpu_memory_used, models_loaded, pinecone_connected }`

---

#### `GET /api/model-info`
Returns active model capabilities and configuration.

---

## 5. Frontend Dashboard

The dashboard is a single HTML file (`face_recognition_advanced.html`) with no build step required — open directly in any modern browser.

| Section | Functionality |
|---|---|
| Dashboard Stats | Total enrolled faces, vector count, processing speed, recognition accuracy |
| Media Processing | Drag-and-drop image/video upload with quality mode selector |
| Face Gallery | View, delete, and update enrolled identities |
| Camera Feed | Real-time webcam stream to backend for live inference |

**Tech Stack:** HTML5, CSS3 (custom properties / dark theme), Vanilla JavaScript ES6+, Fetch API, FontAwesome 6.5.1, Google Fonts (Inter).

No frameworks, no bundler. Zero frontend build complexity.

---

## 6. Vector Database — Pinecone Setup

| Property | Value |
|---|---|
| Provider | Pinecone (Serverless) |
| Cloud | AWS |
| Region | us-east-1 |
| Index Name | `face-recognition-index` |
| Dimensions | 512 |
| Similarity Metric | Cosine |
| Authentication | API key via environment variable |

### Recreating the Index

If the index needs to be recreated from scratch (e.g., new deployment):

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_API_KEY")
pc.create_index(
    name="face-recognition-index",
    dimension=512,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
```

### Metadata Schema (per vector)

```json
{
  "id": "uuid-string",
  "values": [/* 512-dim float array */],
  "metadata": {
    "name": "Person Name",
    "image_path": "static/person_name_timestamp.jpg",
    "enrollment_type": "single | bulk",
    "quality_score": 0.94,
    "angle_index": 0
  }
}
```

---

## 7. Deployment & Environment Setup

### System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| Python | 3.8+ | 3.10+ |
| RAM | 8 GB | 16 GB |
| GPU | None (CPU fallback) | NVIDIA GPU with CUDA 11.x+ |
| Storage | 2 GB | 5 GB |
| OS | Windows / Linux / macOS | Ubuntu 20.04+ or Windows 11 |

### Step-by-Step Setup

**Step 1 — Clone the repository and install dependencies:**

```bash
pip install -r requirements.txt
```

> Remove `dinov3` from `requirements.txt` before installing — it is unused and may cause installation conflicts.

---

**Step 2 — Set Pinecone API Key:**

```bash
# Linux / macOS
export PINECONE_API_KEY="your-pinecone-api-key"

# Windows PowerShell
$env:PINECONE_API_KEY="your-pinecone-api-key"
```

---

**Step 3 — Fix the hardcoded model path (CRITICAL):**

Open `model3.py` and locate the hardcoded path:

```python
# CURRENT (broken on any machine except the original dev's)
model_path = r"C:\Document Local\Projects\Lost & Found with new Face pt model\Models\Face_Models\Face_Detect_last.pt"
```

Replace with an environment variable or relative path:

```python
import os

# RECOMMENDED FIX — relative path
model_path = os.path.join(os.path.dirname(__file__), "models", "Face_Detect_last.pt")

# OR — environment variable
model_path = os.environ.get("YOLO_MODEL_PATH", "./models/Face_Detect_last.pt")
```

Then place `Face_Detect_last.pt` in a `models/` folder at the project root.

---

**Step 4 — Install FFmpeg (for video conversion):**

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org and add to PATH
```

---

**Step 5 — Start the server:**

```bash
python app.py
```

Server starts at `http://127.0.0.1:5000`. Open `face_recognition_advanced.html` in a browser.

---

### Docker Deployment (Recommended for Production)

A `Dockerfile` is not currently included in the repository but is strongly recommended for production. A basic template:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y ffmpeg
RUN pip install -r requirements.txt

ENV PINECONE_API_KEY=""
ENV YOLO_MODEL_PATH="/app/models/Face_Detect_last.pt"

EXPOSE 5000
CMD ["python", "app.py"]
```

---

## 8. Known Issues & Critical Bugs

The following issues have been identified in the current codebase. Each is documented with its location, impact level, and a recommended fix.

---

### CRITICAL — Hardcoded YOLO Model Path

**File:** `model3.py`
**Impact:** Application crashes immediately on startup on any machine other than the original developer's.
**Description:** The YOLO model path is hardcoded as an absolute Windows path:
`C:\Document Local\Projects\Lost & Found with new Face pt model\Models\Face_Models\Face_Detect_last.pt`

**Fix:** Use a relative path or environment variable. See Section 7, Step 3.

---

### CRITICAL — PyTorch Security Bypass (torch.load hack)

**File:** `model3.py`
**Impact:** Security vulnerability. Bypasses PyTorch's protection against malicious pickle files in model weights.
**Description:** To load older YOLO weights, the code temporarily overrides `torch.load` to force `weights_only=False`. This disables security checks.

**Fix:** Re-export the YOLO model weights using the current Ultralytics version to eliminate the need for this override:

```python
# Re-export using current ultralytics
from ultralytics import YOLO
model = YOLO("Face_Detect_last.pt")
model.save("Face_Detect_last_v2.pt")  # saved in safe format
```

---

### HIGH — Global State Camera Bug

**File:** `app.py`
**Impact:** Only one camera session can exist across the entire server at any time. Any second user attempting to start a stream receives an error.
**Description:** `/api/camera/start` uses global variables `camera_active` and `camera_cap` to manage stream state.

**Fix:** Implement session-based or user-token-based camera state management. Each client should have an independent session ID mapped to its own camera context.

---

### HIGH — Missing `clean_and_reindex_database()` Method

**File:** `model3.py`
**Impact:** The `/api/database/cleanup` endpoint silently does nothing. Users triggering a database cleanup get a success response but no action is taken.
**Description:** `app.py` checks for and calls `current_model.clean_and_reindex_database()`, but this method is never implemented in `model3.py`.

**Fix:** Implement the method or remove the endpoint until it is ready:

```python
def clean_and_reindex_database(self):
    # Delete all vectors and re-enroll from local static/ directory
    self.index.delete(delete_all=True)
    # Re-enroll logic here...
    pass
```

---

### MEDIUM — Silent FFmpeg Failure on Video Conversion

**File:** `app.py`
**Impact:** Users uploading `.avi`, `.wmv`, or other non-web-native formats will receive an output video that cannot play in the browser. No error is shown.
**Description:** If FFmpeg is not installed, the conversion endpoint falls back to the original unconverted file silently.

**Fix:** Add explicit FFmpeg availability detection at startup and surface a clear error to the user:

```python
import shutil
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

# In the conversion endpoint:
if not FFMPEG_AVAILABLE:
    return jsonify({"success": False, "error": "FFmpeg not installed. Video conversion unavailable."}), 500
```

---

### MEDIUM — Stale DINOv3 Dependency in `requirements.txt`

**File:** `requirements.txt`
**Impact:** Installation confusion, potential dependency conflict, misleading documentation.
**Description:** `requirements.txt` lists DINOv3 as a dependency but it is not used anywhere in the active codebase.

**Fix:** Remove the DINOv3 entry from `requirements.txt`.

---

## 9. Technology Comparison & Alternatives

This section documents why specific technologies were chosen and how they compare against the most common alternatives. This is intended to help stakeholders and developers evaluate future migration decisions.

---

### 9.1 Face Detection — YOLOv8n vs. Alternatives

| Model | Speed | Accuracy | Occlusion Handling | Ease of Custom Training | Notes |
|---|---|---|---|---|---|
| **YOLOv8n (Used)** | 5/5 | 4/5 | 3/5 | 5/5 | Best for custom dataset training; nano is fastest |
| RetinaFace | 3/5 | 5/5 | 5/5 | 2/5 | Industry standard for accuracy; harder to retrain |
| MediaPipe Face | 5/5 | 3/5 | 2/5 | 1/5 | Google's pipeline; excellent for mobile/edge; not retrainable |
| OpenCV Haar | 4/5 | 2/5 | 1/5 | 1/5 | Used as fallback only; outdated for production |
| MTCNN | 2/5 | 4/5 | 3/5 | 2/5 | Multi-task CNN; slower but landmark-aware |

**Verdict:** YOLOv8n was the correct choice given the requirement for custom dataset training. If occlusion becomes a major use case in future iterations, RetinaFace is the recommended upgrade path.

---

### 9.2 Face Embedding — FaceNet vs. Alternatives

| Model | Embedding Dim | Accuracy | Speed | Ease of Use | Notes |
|---|---|---|---|---|---|
| **FaceNet/InceptionResnetV1 (Used)** | 512 | 4/5 | 4/5 | 5/5 | Well-maintained via facenet-pytorch |
| ArcFace (InsightFace) | 512 | 5/5 | 4/5 | 3/5 | Current state-of-the-art; higher accuracy |
| DeepFace | Variable | 4/5 | 3/5 | 5/5 | Meta-library wrapping multiple backends |
| VGGFace2 (direct) | 512 | 4/5 | 3/5 | 3/5 | Older architecture; superseded by ArcFace |
| DINOv2/v3 | Variable | 3/5 | 2/5 | 2/5 | Not face-specific; general vision transformer |

**Verdict:** FaceNet is a solid, production-proven choice. For higher accuracy requirements in future versions, migrating to **InsightFace (ArcFace + RetinaFace)** is recommended — it is the current industry standard and bundles detection and embedding in one optimized package.

---

### 9.3 Vector Database — Pinecone vs. Alternatives

| Database | Hosting | Cost | Offline Support | Setup Complexity | Scale |
|---|---|---|---|---|---|
| **Pinecone Serverless (Used)** | Fully managed cloud | Pay-per-use | No | Very Low | Enterprise-grade |
| ChromaDB | Self-hosted / local | Free | Yes | Very Low | Small-medium |
| Qdrant | Self-hosted / cloud | Free (self-host) | Yes | Low | Medium-large |
| Milvus | Self-hosted | Free | Yes | High | Enterprise |
| pgvector (PostgreSQL) | Self-hosted | Free | Yes | Medium | Medium |
| Weaviate | Self-hosted / cloud | Free tier | Yes | Medium | Medium-large |

**Verdict:** Pinecone was the right choice for rapid development — zero infrastructure management and instant scalability. However, for air-gapped deployments, privacy-sensitive use cases, or cost-sensitive production, **Qdrant** is the recommended alternative. It is performant, open-source, and can run fully offline with a Docker container.

---

### 9.4 API Framework — Flask vs. FastAPI

| Framework | Async Support | Performance | ML Ecosystem Fit | Ease of Use | Auto Docs |
|---|---|---|---|---|---|
| **Flask (Used)** | Synchronous | Medium | 4/5 | 5/5 | Manual |
| FastAPI | Native async | High | 4/5 | 4/5 | Auto (Swagger) |
| Django REST | Synchronous | Medium | 3/5 | 3/5 | Via plugins |

**Verdict:** Flask is appropriate for a single-user or low-concurrency prototype. For production deployment with concurrent users (especially given the camera feed and video processing workloads), **FastAPI** is strongly recommended. Its async request handling prevents the server from blocking during heavy ML inference calls, and it auto-generates Swagger API documentation.

---

### 9.5 Combined Pipeline Recommendation for Future Versions

| Component | Current | Recommended Upgrade |
|---|---|---|
| Detection | YOLOv8n (custom) | Keep YOLOv8n (or RetinaFace for occlusion) |
| Embedding | FaceNet (VGGFace2) | InsightFace / ArcFace |
| Vector DB | Pinecone (cloud) | Qdrant (self-hosted) for offline; keep Pinecone for cloud |
| API | Flask | FastAPI |
| Deployment | Manual local | Docker + environment variables |

---

## 10. Future Work & Roadmap

The following improvements are recommended for subsequent development phases. They are listed in order of impact vs. effort.

### High Priority (Fix Before Production)

1. **Fix hardcoded model path** — Convert to relative path or environment variable (see Section 8)
2. **Resolve PyTorch security bypass** — Re-export model weights in safe format (see Section 8)
3. **Implement `clean_and_reindex_database()`** — Complete the missing method in `model3.py`
4. **Add FFmpeg availability check** — Surface clear errors instead of silent fallbacks
5. **Remove DINOv3 from `requirements.txt`** — Prevents installation confusion

### Medium Priority (Before Scaling)

6. **Replace Flask with FastAPI** — Required for concurrent user support and ML workload async handling
7. **Session-based camera management** — Replace global state with per-user session tokens
8. **Dockerize the application** — Eliminates environment setup issues across machines
9. **Add input validation** — File type checking, size limits, and malformed request handling on all endpoints

### Lower Priority (Feature Enhancements)

10. **Evaluate ArcFace / InsightFace migration** — For improved recognition accuracy on difficult cases
11. **Occlusion handling** — Specialized training data and architecture for partially visible faces
12. **Multi-camera support** — Cross-camera identity tracking with stream synchronization
13. **Edge deployment optimization** — Model quantization (INT8/FP16) for deployment on lower-power hardware
14. **Dataset expansion** — Augment with additional identities and extreme conditions (night, masks, glasses)
15. **Embedding versioning** — Track which model version generated each stored embedding to allow safe re-indexing after model updates

---

## 11. Glossary

| Term | Definition |
|---|---|
| **Embedding** | A numerical vector representing a face's identity features in high-dimensional space |
| **Cosine Similarity** | A measure of similarity between two vectors based on the angle between them (1.0 = identical, 0.0 = unrelated) |
| **YOLOv8n** | You Only Look Once v8 nano — a real-time object detection model; nano is the smallest/fastest variant |
| **FaceNet** | A deep learning model that maps face images to 512-dimensional embedding space |
| **InceptionResnetV1** | The neural network architecture used within FaceNet |
| **VGGFace2** | A large-scale face recognition dataset used to pretrain the FaceNet model |
| **Pinecone** | A cloud-hosted vector database optimized for similarity search at scale |
| **NMS** | Non-Maximum Suppression — removes redundant overlapping bounding boxes during detection |
| **CUDA** | NVIDIA's parallel computing platform enabling GPU-accelerated ML inference |
| **Bulk Enrollment** | Enrolling multiple images of one person to improve recognition accuracy across angles |
| **ArcFace** | State-of-the-art face recognition loss function and model; part of the InsightFace library |
| **DINOv2/v3** | A self-supervised vision transformer from Meta; listed in requirements but not used in this project |
| **FFmpeg** | An open-source multimedia processing tool used for video format conversion |

---

*Report prepared as part of FaceVault project handover. All sections reflect the state of the codebase as reviewed and should be verified against the live repository before production deployment.*