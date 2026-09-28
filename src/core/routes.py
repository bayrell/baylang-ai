"""
API роуты приложения.
Содержит основные эндпоинты и подключает auth роуты.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from core.app import get_container, get_config
from core.config import Config

router = APIRouter()
container = get_container()
template = container.get("template")

index_page = template.from_string("""<!DOCTYPE html>
<body>
  <div class="app_container"></div>
  <link rel="stylesheet" href="main.css" />
  <script src="main.js"></script>
</body>""")


@router.get("/", response_class=HTMLResponse)
def action_index():
    return index_page.render()


@router.get("/env")
async def env(config: Config = Depends(get_config)):
    value = config.get("DEBUG")
    message = f"Here is an example of getting an environment variable: {value}"
    return {"message": message}

