# Prompt design: still images and image-to-video

## Still-image prompt structure

Write each prompt as short, direct English instructions, followed by the original Spanish visual beat as source material. Gemini image generation officially lists Spanish (es-MX) among its best-performing languages, so English is a useful cross-provider default, not a claim that Spanish image prompts always perform worse.

Include only details that affect the output, in this order:

1. Deliverable: one vertical 9:16 still for a specific scene.
2. Reference role: character identity/colors/materials, style, or full composition. State which image controls which.
3. One concrete scene beat: interpret the approved narration visually; never put narrated words into the artwork.
4. Framing and composition: shot scale, clear focal subject, readable silhouette, safe margin.
5. Style/light/setting: match the source reference unless the story specifically requires a change. Do not hard-code a palette, city, time of day, or anime style for every topic.
6. Compact exclusions: no lettering, subtitles, logos, watermarks, UI, collage, or unsupported characters/events.

For the Pipeline's current anime-character reference flow, preserve canonical colors and recognizable design from the uploaded source, but create a new scene, pose, and composition. The previously tested character reference is authoritative; a generated image from an earlier scene can be a scene/style reference only when the user explicitly wants that.

## Image-to-video prompt structure

The animation prompt is about the uploaded still, not the script. Use this order:

1. State that the uploaded still is the starting frame and the output is one continuous shot.
2. Lock identity and visible design: face, proportions, pose, costume, markings, props, palette, background layout, lighting, and visual medium.
3. Choose one camera move only if it suits the composition; no orbit for a flat illustration or movement that reveals unseen space.
4. Specify one subtle motion from visible elements only. Keep other elements still. If the character's identity is at risk, animate only the existing effect or environment.
5. State concise exclusions: no cuts, morphing, new entities/effects, text, dialogue, or audio when unwanted.

Do not mention the narration, “hook,” scene title, argument, theory, CTA, seconds, or required duration. The user's video generator chooses clip length through its controls, if it exposes them; prompt text must not claim duration can be controlled.

## Language and model choice

Google documents English as fully supported for Veo video prompting and says other languages may work but are unevaluated; use English for the animation instruction block when using Veo. Gemini image generation separately lists Spanish (es-MX) as a best-performing language. OpenAI's image prompting guide emphasizes explicit reference roles and preserving specified details; it does not claim English is inherently better. Keep prompts provider-neutral and follow the language support stated for the actual model/interface.

English wording does not guarantee a better result. Preserve the approved Spanish beat as quoted input, then compare output quality when a provider explicitly supports Spanish. When diagnosing a failure, first identify whether it came from missing reference, conflicting instructions, unsupported UI controls, prompt ambiguity, or model limits; change one cause at a time.

## Official guidance

- [Google DeepMind Veo prompt guide](https://deepmind.google/models/veo/prompt-guide/)
- [Google Flow: create videos and animate images](https://support.google.com/flow/answer/16353334?hl=en)
- [Gemini API: Veo 3.1 language support and image-to-video prompting](https://ai.google.dev/gemini-api/docs/veo)
- [Gemini API: image generation languages and reference images](https://ai.google.dev/gemini-api/docs/image-generation)
- [OpenAI: image prompting and explicit reference roles](https://developers.openai.com/api/docs/guides/image-prompting)
- [OpenAI: Sora product availability](https://openai.com/index/creating-with-sora-safely/) — product availability can change; verify the user's current interface before relying on a video tool.
