from fastapi.templating import Jinja2Templates

from .formatting import format_datetime, format_json

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["datetime_br"] = format_datetime
templates.env.filters["json_pretty"] = format_json
