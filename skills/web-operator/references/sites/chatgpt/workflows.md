# ChatGPT Image Workflows

This file describes the `chatgpt.com/images` workflow bundled with the skill.
The workflow drives a signed-in ChatGPT browser tab through CDP, waits for a new
generated image, then downloads the image bytes from inside the authenticated
page context.

## Scope

- Generate a new image from a text prompt on `https://chatgpt.com/images/`.
- Save the generated image to a local file.
- Return metadata such as file id, conversation id, dimensions, byte size, and
  conversation URL when `--json` is used.
- Not in scope: editing existing images, uploading reference images, batch
  generation, model selection, style presets, or bypassing ChatGPT login/usage
  limits.

## Command

```bash
omp web-operator generate-image chatgpt "<prompt>" \
  [--out <path>] \
  [--target <prefix>] \
  [--timeout <seconds>] \
  [--overwrite] \
  [--json]
```

## Output

Without `--json`, stdout is the saved file path.

With `--json`, stdout is a JSON object:

```json
{
  "site": "chatgpt",
  "prompt": "a blue circle on white background",
  "path": "/home/bruce/Downloads/chatgpt-image-2026-06-16T01-40-00-000Z.png",
  "mime_type": "image/png",
  "bytes": 843441,
  "width": 1254,
  "height": 1254,
  "conversation_id": "6a30a90f-25f0-83e8-93b4-eee81277a0a3",
  "file_id": "file_0000000011ec71fdbdd0fc808a319855",
  "file_name": "user-.../image.png",
  "alt": "Generated image: ...",
  "conversation_url": "https://chatgpt.com/c/...",
  "target": "17BA601B"
}
```

## SOP

1. Find an existing `https://chatgpt.com/images/` tab, or open one when
   `--target` is omitted.
2. Navigate the target to `https://chatgpt.com/images/` and wait for the image
   composer (`#prompt-textarea`).
3. Fail with a login-specific error if the page shows sign-in prompts instead
   of the composer.
4. Record current generated-image file ids from rendered `estuary/content` image
   URLs.
5. Focus the composer, type the prompt with CDP input events, and click the
   enabled send button.
6. Poll the page until a new generated image appears whose `file_...` id was not
   present before submission.
7. Fetch `/backend-api/files/download/<file_id>?conversation_id=<id>` inside the
   page context when possible to resolve the signed `download_url`.
8. Configure Chrome download behavior for the output directory.
9. Trigger a browser download for the signed image URL from the authenticated
   page, wait for the downloaded file, rename it to `--out` when needed, and
   validate the image header.
10. Close the ChatGPT tab opened or auto-selected by the command before
    reporting success. Keep the tab open only when the caller passed
    `--target` explicitly.

## Notes

- Direct shell downloads of the rendered `estuary/content` URL can return
  `403 Forbidden`; use the authenticated browser page context for the binary
  fetch.
- The command consumes ChatGPT image generation quota and requires the user to
  already be signed in in Chrome.
- `--target` accepts the same target prefix shown by `omp web-operator page list`; explicitly targeted tabs are left open.
- Default output is `~/Downloads/chatgpt-image-<timestamp>.png`.
- Use `--overwrite` only when replacing an existing file is intentional.
