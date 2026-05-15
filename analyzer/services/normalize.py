from analyzer.schemas.analysis import AnalyzeRequest


def format_script(req: AnalyzeRequest) -> str:
    return _normalize_input_text(req.input_text)


def _normalize_input_text(text: str) -> str:
    raw = text.strip()
    if not raw:
        return raw

    import re

    t = raw.replace("\r\n", "\n").replace("\r", "\n").strip()

    m_expected = re.search(r"(?im)^\s*expected\s+system\s+behaviou?r\s*:?\s*$", t)
    if m_expected:
        t = t[: m_expected.start()].rstrip()

    title = None
    m_title = re.search(r"(?im)^\s*title\s*:\s*(.+?)\s*$", t)
    if m_title:
        title = m_title.group(1).strip()

    def _find_header(name: str) -> tuple[int, int, str] | None:
        m = re.search(rf"(?im)^\s*{re.escape(name)}\s*:?\s*(.*?)\s*$", t)
        if not m:
            return None
        return (m.start(), m.end(), (m.group(1) or "").strip())

    scene_pos = _find_header("scene")
    dialogue_pos = _find_header("dialogue") or _find_header("dialog")

    if scene_pos and dialogue_pos and scene_pos[0] < dialogue_pos[0]:
        scene_inline = scene_pos[2]
        scene_rest = t[scene_pos[1] : dialogue_pos[0]].strip()
        scene_text = (scene_inline + ("\n" + scene_rest if scene_rest else "")).strip()

        dialogue_inline = dialogue_pos[2]
        dialogue_rest = t[dialogue_pos[1] :].strip()
        dialogue_text = (dialogue_inline + ("\n" + dialogue_rest if dialogue_rest else "")).strip()

        title_text = title or "Untitled"
        return (
            f"Title: {title_text}\n\n"
            f"Scene\n{scene_text}\n\n"
            f"Dialogue\n{dialogue_text}"
        ).strip()

    return raw
