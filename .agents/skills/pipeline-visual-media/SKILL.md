---
name: pipeline-visual-media
description: Prepare or revise the manual image-generation and image-to-video prompts for this content pipeline, and guide the handoff from approved script to assembled MP4.
---

# Pipeline visual media

Use this skill when preparing, generating, reviewing, or repairing the still images and animation clips for a pipeline `CONTENT-ID`.

Read [references/workflow.md](references/workflow.md) for the complete handoff and troubleshooting decisions. Read [references/prompting.md](references/prompting.md) when writing or revising the image or animation prompts.

Keep narration and media prompts separate: the image prompt turns a specific scene beat into a still; the animation prompt describes only motion visible in that still. Do not put a hook label, narration, discussion question, duration, or scene timing in an animation prompt. The user joins the generated clips manually before starting local voice and subtitle production.

For this repository, preserve the numbered pairing: `imagenes/prompt_XX.txt` → `imagenes/imagen_XX.png` → `animar_imagenes/prompt_XX.txt` → `animar_imagenes/clip_XX.mp4`. Never overwrite finished media or alter a READY job's outputs while updating templates. Make the requested prompt/skill changes in the repository and keep the personal installed copy of this skill in sync.
