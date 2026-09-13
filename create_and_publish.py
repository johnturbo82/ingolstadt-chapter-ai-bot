#!/usr/bin/env python3
"""Erstellt per GitHub Copilot CLI einen Blogpost und veröffentlicht ihn via WordPress REST API."""
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
WP_URL = os.environ.get("WP_URL", "https://www.ingolstadt-chapter.de/wp-json/wp/v2/posts")
WP_USER = os.environ.get("WP_USER")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD")


def build_prompt() -> str:
    skill_content = (SCRIPT_DIR / "SKILL.md").read_text(encoding="utf-8")
    heute = date.today().isoformat()
    return f"{skill_content}\n\nZusatzkontext: Erstelle den Beitrag für diese Woche (Datum: {heute})."


def run_copilot(prompt: str) -> str:
    result = subprocess.run(
        ["copilot", "-p", prompt, "-s", "--allow-all"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def extract_valid_json(raw: str) -> dict:
    # Fall 1: Ausgabe ist bereits valides JSON.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fall 2: JSON in ```json ... ```-Codeblock extrahieren.
    match = re.search(r"```json\s*(.*?)```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Fall 3: Alles zwischen erster { und letzter } extrahieren.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Copilot-Ausgabe enthält kein valides JSON.")


def validate_post(post: dict) -> dict:
    if post.get("status") == "skip":
        return post

    required_fields = ("title", "content", "status")
    missing_fields = [field for field in required_fields if not post.get(field)]
    if missing_fields:
        raise ValueError(
            "Copilot-Ausgabe enthält nicht alle erforderlichen Felder: "
            + ", ".join(missing_fields)
        )
    content = post["content"]
    if "<!-- wp:" not in content:
        raise ValueError("Der Content enthält kein Gutenberg-Block-Markup.")
    if "<!--more-->" not in content:
        block_end = re.search(r"<!--\s*/wp:[^>]+-->", content)
        if block_end is None:
            raise ValueError("Kein abgeschlossener Gutenberg-Block für den More-Tag gefunden.")
        insert_at = block_end.end()
        post["content"] = (
            content[:insert_at]
            + "\n<!--more-->\n"
            + content[insert_at:]
        )
    return post


def publish(post: dict) -> None:
    if not WP_USER or not WP_APP_PASSWORD:
        raise RuntimeError(
            "Fehler: WP_USER und WP_APP_PASSWORD müssen als Umgebungsvariablen gesetzt sein."
        )
    response = requests.post(WP_URL, auth=(WP_USER, WP_APP_PASSWORD), json=post, timeout=30)
    response.raise_for_status()
    print(f"Beitrag veröffentlicht: {response.json().get('link', response.url)}")


def main() -> int:
    prompt = build_prompt()
    raw_output = run_copilot(prompt)

    try:
        post = validate_post(extract_valid_json(raw_output))
    except ValueError as exc:
        print(f"Fehler: {exc} Antwort wurde nicht gesendet.", file=sys.stderr)
        print("--- Copilot-Ausgabe (gekürzt) ---", file=sys.stderr)
        print("\n".join(raw_output.splitlines()[:40]), file=sys.stderr)
        return 1

    if post.get("status") == "skip":
        print(f"Kein Beitrag erstellt: {post.get('reason', 'Kein geeignetes Thema gefunden.')}")
        return 0

    publish(post)
    return 0


if __name__ == "__main__":
    sys.exit(main())
