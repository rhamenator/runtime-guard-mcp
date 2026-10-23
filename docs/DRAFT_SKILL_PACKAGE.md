# Draft companion skill package

Run from a saved checkout with Python 3.11+ and Git:

```sh
python scripts/package_draft_skill.py --ref HEAD --output /path/to/new-output
```

The tool resolves the requested commit once, reads only the approved SKILL.md, LICENSE and NOTICE Git blobs, and creates `runtime-guard-draft.zip` plus an external JSON provenance/checksum manifest. Working-tree edits, untracked files and development artifacts are excluded. It does not modify the skill source, install a server, submit to a marketplace or publish a release. Existing outputs are preserved; choose a fresh directory for each run.

The ZIP contains one top-level `runtime-guard/` folder with SKILL.md at its root and the license/notice. No binaries, credentials or server installation are bundled. The source skill's supported frontmatter is deliberately narrow: exactly the approved name and one plain ASCII description line. Unexpected YAML syntax fails for review rather than being interpreted by a new dependency. Obvious private-key/local-home content in the skill rejects; this is not a comprehensive secret scanner, so manual content/claim review remains required.

Packaging always injects a draft/non-submission notice after frontmatter. It uses fixed ZIP timestamps, regular nonexecutable modes, stable ordering and stored bytes, avoiding compressor-version variability. It reopens and checks every member. The external manifest records the immutable source commit, builder digest, per-member/archive SHA-256 and pending review status. Two builds from the same source/builder produce identical archive/manifest bytes; CI compares both on Python 3.11–3.14.

The companion still requires a separately installed/configured advisory server and the permissions/client limitations described in its instructions. CI builds a fresh server wheel and runs installed client/API probes in the same job. This draft evidence does not replace final exact-candidate native-client, adversarial, source-archive/wheel/provenance and independent human review gates. No listing-ready or stable-release claim is made. A submission-ready artifact requires a separate explicit readiness decision and claim-to-test review; do not submit this draft.
