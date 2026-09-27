# Manual image and animation workflow

## Choose the correct references

Before prompting, inspect the approved script, scene list, current job handoff, and supplied references.

- A **character reference** defines identity: face, silhouette, costume, markings, colors, and materials. Upload the actual image; naming the character in text does not attach a reference.
- A **style reference** defines only the medium or rendering treatment. Label it separately and do not let it replace character identity.
- A **scene reference** defines the whole starting composition. If the goal is to create a new scene with the same character, say so; do not ask the image model both to preserve the entire reference frame and invent a different setting.
- If there are multiple references, explicitly say what each one controls. Use the approved canonical character image as the source of truth when later generated scene images have drifted.
- If no reference exists, describe only established story facts. Do not invent canonical colors, costume details, powers, or events. If those details matter and are unknown, ask for the missing reference or fact before generation.

## Create each still image

1. Open `imagenes/prompt_XX.txt` and upload the actual character reference before pasting it.
2. Generate one image for that numbered scene. The prompt must describe one visible moment from that scene's narration, not reproduce the narration as lettering.
3. Save the accepted result as `imagenes/imagen_XX.png`; keep the same number for its animation prompt and clip.
4. Inspect before moving on: recognizable character and reference colors, one clear action or consequence, appropriate scene setting, legible vertical composition, no accidental text or extra characters.
5. If it fails, retry with one precise correction (for example, “restore the reference's orange and teal markings; keep the pose and background unchanged”). Reattach the canonical reference. Do not replace all successful instructions with a long list of unrelated negatives.

For more than one character, state who appears and what each is doing. Do not put every narrated beat into one image. For abstract narration, use the clearest specific consequence already stated in the script. If the beat cannot be represented without adding unsupported canon, choose an established symbol or ask the user which visual interpretation they prefer.

## Animate the matching still

1. Open `animar_imagenes/prompt_XX.txt` and upload the matching `imagenes/imagen_XX.png` as the image-to-video/start-frame input.
2. Paste the animation prompt by itself. It must describe a single continuous shot, one restrained camera treatment at most, and a small amount of motion in elements already visible in the uploaded image.
3. Save the result as `animar_imagenes/clip_XX.mp4`. Do not include seconds, duration targets, narration, hook labels, or a call to action in this prompt.
4. Review identity, face, costume, composition, and motion. If the subject warps, becomes a new character, or the model invents objects, reduce motion or lock the camera and animate only an existing light/particle/effect.

Use a slow push-in for a clear focal subject, a subtle horizontal slide for an established environment, a small pullback/tilt only when it will not reveal invented space, or a nearly locked frame when the image is crowded or geometry is delicate. Avoid orbiting a flat illustration; it can invent unseen sides and distort the drawing. If the character should remain perfectly still, say so and animate only a visible effect or atmosphere. If there is no suitable visible motion, a stable shot is preferable to invented action.

## Special cases and recovery

- **The model ignores the reference:** re-upload it, name its role in the first sentence, and list the few identity traits that must stay fixed. Do not rely on a character name alone.
- **The character's colors change:** describe the colors as identity-critical and use the reference as the source of truth. Remove global color schemes that conflict with it.
- **The image copies the reference composition:** clarify that the reference is for character identity only; request a new pose, shot, and setting.
- **The result contains words, UI, or multiple panels:** ask for one clean single-frame illustration with no readable writing or layout elements.
- **Animation changes the design or framing:** use less motion, remove orbit/parallax, lock the camera, and animate one already-visible detail.
- **Animation looks static:** identify one visible source of motion from the actual image (energy, particles, reflections, cloth, hair, or light). Ask for a restrained motion there; never add a new event just to create movement.
- **The video tool is absent or rejects image input:** check current account, region, model, and interface support. Treat that as a tool-availability issue, not automatically as a prompt defect. Do not switch to a paid API or cloud workflow without a user request.
- **There are fewer generated clips than scenes:** keep scene numbering and do not silently stretch one clip across unrelated narration. Ask which scenes should share footage or whether another clip should be generated.
- **The user provides clips rather than stills:** accept only the assets that match the current job, preserve their numbering/order, and do not regenerate media without being asked.

## Assemble and hand off to the local pipeline

After the user accepts the clips, they may either combine them in numeric order and save `video_completo.mp4` at the root of `videos/subir/CONTENT-ID/`, or leave numbered `clip_XX.mp4` files in `videos/subir/CONTENT-ID/animar_imagenes/` for the worker to assemble. The worker retains all inputs under `subir` for retries. After successful QA, it copies the final subtitled video to `videos/terminado/CONTENT-ID.mp4`; it also retains the working master under `data/assets/CONTENT-ID/masters/`.

`videos/subir` and `videos/terminado` are created at startup and are excluded from Git except for empty directory markers. Set `MEDIA_INBOX_HOST_PATH` in `.env` to move them to another host folder. Never put a user-specific absolute path in shared docs or prompt files.

A READY job and its final video are historical output. Update generator templates for future jobs; do not replace its prompts or media unless the user asks to reopen that job.
