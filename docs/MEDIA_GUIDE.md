# 📸 Media Creation Guide for AI Learning Agent

## 🎯 **Required Screenshots and Videos**

### Screenshots to Capture (save as PNG files):

#### 1. **main-interface.png**
- **What**: Full web interface at http://localhost:5005
- **Show**: Main chat interface with a sample conversation
- **Size**: 1200x800 pixels
- **Tools**: Browser screenshot or Snipping Tool

#### 2. **reasoning-chain.png**  
- **What**: Chat with reasoning toggle ON
- **Show**: The 6-step reasoning process visualization
- **Query**: "What are my upcoming assignments?"
- **Highlight**: The reasoning steps with emojis

#### 3. **classroom-integration.png**
- **What**: Backend logs or course list
- **Show**: "Found 8 active courses" and "89 indexed content items"
- **Tools**: Terminal screenshot showing initialization

#### 4. **study-plan.png**
- **What**: Generated study plan response
- **Query**: "Create a study plan for HS 103"
- **Show**: Structured study plan with weeks and tasks

#### 5. **mobile-view.png** & **tablet-view.png**
- **What**: Responsive design on different screen sizes
- **Tools**: Browser developer tools (F12) device emulation

#### 6. **architecture-diagram.png**
- **What**: System architecture flowchart
- **Tools**: Draw.io, Lucidchart, or similar
- **Content**: All components from Flask → Gemini → ChromaDB

### Videos to Record (save as MP4 files):

#### 1. **full-demo.mp4** (5 minutes)
- Start application: `python app_web.py`
- Open browser to localhost:5005
- Show course initialization
- Ask 3-4 different questions
- Toggle reasoning on/off
- Generate a study plan
- Show different course content

#### 2. **reasoning-toggle.mp4** (2 minutes)
- Ask same question twice:
  - First with reasoning OFF
  - Then with reasoning ON
- Highlight the differences in response length
- Show the reasoning steps appearing

#### 3. **classroom-demo.mp4** (3 minutes)
- Show Google Classroom integration working
- Display course list
- Show content being indexed
- Query course-specific information

## 🛠️ **Tools for Media Creation**

### Screenshot Tools:
- **Mac**: Cmd+Shift+4 (area), Cmd+Shift+3 (full screen)
- **Windows**: Snipping Tool, Win+Shift+S
- **Browser**: F12 → Device toolbar for responsive screenshots

### Screen Recording Tools:
- **Mac**: QuickTime Player (File → New Screen Recording)
- **Windows**: Xbox Game Bar (Win+G), OBS Studio
- **Cross-platform**: OBS Studio (free), Loom

### Diagram Creation Tools:
- **Free**: Draw.io (diagrams.net), Canva
- **Online**: Lucidchart, Miro
- **Code**: Mermaid (already in README)

## 📝 **Step-by-Step Media Creation**

### Step 1: Prepare Your System
```bash
cd /Users/tanishka/Downloads/final
source venv_compatible/bin/activate
python app_web.py
```

### Step 2: Open Browser
```
http://localhost:5005
```

### Step 3: Capture Screenshots
1. **Main Interface**: Home page with chat ready
2. **Reasoning Chain**: Toggle ON, ask "What are my upcoming assignments?"
3. **Study Plan**: Ask "Create a study plan for HS 103"
4. **Mobile View**: Use browser dev tools (F12) → Device toolbar

### Step 4: Record Videos
1. **Start recording**
2. **Navigate through features**
3. **Speak clearly** (optional narration)
4. **Show cursor movements**
5. **Keep videos under 10MB if possible**

### Step 5: Optimize Files
```bash
# Compress images (if needed)
# Use online tools or ImageOptim (Mac)

# Compress videos (if needed)
# Use HandBrake or online compressors
```

### Step 6: Add to Repository
```bash
# Copy files to docs folders
cp screenshot.png docs/images/main-interface.png
cp video.mp4 docs/videos/full-demo.mp4

# Commit to git
git add docs/
git commit -m "Add screenshots and demo videos"
```

## 🌐 **Alternative: Use GitHub/Online Hosting**

If files are too large for repository:

### Option 1: GitHub Releases
```markdown
![Screenshot](https://github.com/username/repo/releases/download/v1.0/screenshot.png)
```

### Option 2: External Hosting
```markdown
![Screenshot](https://i.imgur.com/abc123.png)
<video src="https://drive.google.com/file/d/xyz/preview"></video>
```

### Option 3: YouTube for Videos
```markdown
[![Demo Video](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=VIDEO_ID)
```

## 🎨 **Making Great Screenshots**

### Tips for Professional Screenshots:
1. **Clean Interface**: Close unnecessary browser tabs
2. **Good Contrast**: Use light mode if dark text is hard to read
3. **Full Content**: Show complete reasoning chains
4. **Consistent Size**: Keep all screenshots similar dimensions
5. **Add Annotations**: Use arrows or highlights for key features

### Sample Queries for Screenshots:
- "What are my upcoming assignments?"
- "Create a study plan for HS 103"
- "Help me understand the group presentation requirements"
- "When is my next deadline?"

## 📏 **Recommended Dimensions**

### Screenshots:
- **Desktop**: 1200x800px or 1400x900px
- **Mobile**: 375x667px (iPhone) or 360x640px (Android)
- **Tablet**: 768x1024px (iPad) or 800x1280px (Android)

### Videos:
- **Resolution**: 1280x720 (720p) or 1920x1080 (1080p)
- **Frame Rate**: 30fps
- **Length**: 2-5 minutes per video
- **Format**: MP4 (best compatibility)

## 🚀 **Quick Start Commands**

```bash
# Create screenshot (Mac)
screencapture -i docs/images/main-interface.png

# Start screen recording (Mac with sound)
screencapture -v docs/videos/demo.mov

# Convert MOV to MP4 (if needed)
ffmpeg -i docs/videos/demo.mov docs/videos/demo.mp4
```

---

**Next Steps:**
1. Start your Flask application
2. Capture the required screenshots
3. Record the demo videos  
4. Update file paths in README if needed
5. Test that all media displays correctly

This will make your README much more engaging and professional! 📸🎥