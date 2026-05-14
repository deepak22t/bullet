from analyzer.schemas.analysis import AnalyzeRequest


def format_script(req: AnalyzeRequest) -> str:
    return (
        f"Title: {req.title.strip()}\n\n"
        f"Scene\n{req.scene.strip()}\n\n"
        f"Dialogue\n{req.dialogue.strip()}"
    )
