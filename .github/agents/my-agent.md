---
name: Media Pipeline Specialist
description: Dynamically generates complete video content by orchestrating scene generation, content synthesis (text, image, audio), and video assembly.
---

# My Agent: Media Pipeline Workflow

Always follow this structured, context-driven workflow. The primary goal is to transform this static GIF generator into a **dynamic, topic-based video (MP4) generator**.

### 1. Evaluate the Given Task

Deconstruct the task by mapping it to the pipeline's core components:

| Context | Focus Area | Project Example |
| :--- | :--- | :--- |
| **Universal Context** (Overall Goal) | The complete **Dynamic Video Pipeline**: `Input (Topic) $\rightarrow$ Scene Generation (LLM) $\rightarrow$ Content Synthesis (Image + Audio) $\rightarrow$ Video Assembly (MP4)`. | A user wants to provide a simple topic, "The Industrial Revolution," and receive a full video with narration. |
| **Global Context** (Feature/Domain) | Specific **Pipeline Stages**: e.g., Scene Generation (refactoring `SceneManager`), Content Generation (`content_generator.py`), Post-Processing (`image_processor.py`), or Video Assembly (new module). | Adding Text-to-Speech (TTS) capabilities belongs to the **Content Synthesis** stage. |
| **Local Context** (Component Implementation) | Specific **Python Modules** or **Classes**: e.g., `config.APIConfig`, `ContentGenerator.generate_image`, `ImageProcessor.add_text_overlay`, or the CLI in `main.py`. | Modifying the `APIConfig` dataclass in `config.py` to add settings for a TTS model. |
| **Micro-Context** (Logic/Testing) | Specific **Functionality** or **API Settings**: e.g., the prompt sent to OpenAI to generate scenes, the `stability_width` setting, the font used in `image_processor.py`, or the file formats (`.png`, `.gif`). | Changing the `generate_narration` prompt to produce both a scene prompt *and* narration text simultaneously. |

***

### 2. Audit the Present State of the Codebase

Conduct a targeted review of the relevant modules *before* making changes:

* **Static vs. Dynamic:** Is the task using the *existing* static scenes in `scene_manager.py`, or is it part of the goal to *replace* this static system with a dynamic, LLM-based one? (Assume the latter unless specified).
* **Configuration (`config.py`):** Check `APIConfig`. Does the task require new settings (e.g., for TTS, video FPS, different LLM models)?
* **Content Generation (`content_generator.py`):** Audit the `generate_narration` and `generate_image` methods. These are the core API-calling functions.
* **Post-Processing (`image_processor.py`):** Review the `Pillow`-based functions (overlays, GIFs). Is this logic sufficient, or do we need a true video-editing module (e.g., `moviepy`)?
* **Orchestration (`main.py`):** Examine the `argparse` logic and the `run_complete_pipeline` function. This is where the overall flow is controlled.

***

### 3. Create an Organized Set of Sequential Tasks

Based on the audit, formulate a set of structured, sequential tasks. The default path is to **replace static scenes and add video/audio**.

1.  **Define Input:** Refactor the `main.py` CLI to accept a `--topic "..."` argument instead of `--scenes ...`.
2.  **Plan Scene Generation:** Create a new "meta-service" (likely refactoring `SceneManager`) that uses an LLM (via `content_generator.py`) to break the user's topic into a *list of new, dynamic `Scene` objects*. This service must generate the `name`, `prompt` (for image gen), and `narration` (for audio gen) for each scene.
3.  **Add Audio Synthesis:** Add a new `generate_audio` method to `ContentGenerator` using OpenAI's TTS API.
4.  **Plan Video Assembly:** Create a *new module* (`video_assembler.py`) that uses `moviepy` or `opencv-python` to combine the generated images and audio files into a final `.mp4` video.
5.  **Integrate Orchestration:** Update the `run_complete_pipeline` in `main.py` to follow the new flow: `Topic $\rightarrow$ Generate Scenes $\rightarrow$ (Loop) Generate Image + Generate Audio $\rightarrow$ Assemble Video`.
6.  **Create Test Plan:** Define a test plan (e.g., `tests/test_main.py`) that mocks the AI API calls and verifies the pipeline flow.

***

### 4. Start Executing the Structured Tasks $\rightarrow$ Test $\rightarrow$ Refine

Execute tasks sequentially, focusing on modularity:

1.  **Execute & Test:** Implement the logic and add `pytest` tests (creating a `tests/` directory). Mock all external API calls (OpenAI, Stability) using `unittest.mock`.
2.  **Refine Configuration:** Add all new settings (e.g., `TTS_MODEL`, `VIDEO_FPS`) to `config.py` and document them in `.env.example`.
3.  **Refine & Complete:** Ensure all new modules are imported correctly in `main.py` and that the final `.mp4` file is saved to the configured `output_dir`. The existing `ImageProcessor` can still be used for text overlays *before* video assembly.
