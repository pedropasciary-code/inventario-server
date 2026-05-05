import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import (
    get_admin_session_user,
    get_csrf_token,
    get_db,
    get_session_user_record,
    validate_csrf_token,
)
from ..templating import templates
from ..utils import utc_now

router = APIRouter(prefix="/topology")


def _list_context(request: Request, db: Session, session_user: str, is_admin: bool, **extra):
    topologies = db.query(models.Topology).order_by(models.Topology.name).all()
    return templates.TemplateResponse(
        request,
        "topology_list.html",
        {
            "session_user": session_user,
            "session_is_admin": is_admin,
            "csrf_token": get_csrf_token(request),
            "topologies": topologies,
            **extra,
        },
    )


@router.get("", response_class=HTMLResponse)
def topology_list(request: Request, db: Session = Depends(get_db)):
    user = get_session_user_record(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return _list_context(request, db, user.username, user.is_admin)


@router.post("", response_class=HTMLResponse)
def create_topology(
    request: Request,
    name: str = Form(...),
    description: str = Form(default=""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    name = name.strip()
    if not name:
        return _list_context(request, db, session_user, True, error="O nome não pode ficar vazio.")

    topology = models.Topology(name=name, description=description.strip() or None)
    db.add(topology)
    db.commit()
    return RedirectResponse(url=f"/topology/{topology.id}", status_code=303)


@router.get("/{topology_id}", response_class=HTMLResponse)
def topology_detail(topology_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user_record(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    topology = db.query(models.Topology).filter(models.Topology.id == topology_id).first()
    if not topology:
        raise HTTPException(status_code=404, detail="Topologia não encontrada")

    assets = db.query(models.Asset).order_by(models.Asset.hostname).all()

    return templates.TemplateResponse(
        request,
        "topology_detail.html",
        {
            "session_user": user.username,
            "session_is_admin": user.is_admin,
            "csrf_token": get_csrf_token(request),
            "topology": topology,
            "assets": assets,
        },
    )


@router.get("/{topology_id}/data")
def topology_data(topology_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user_record(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    topology = db.query(models.Topology).filter(models.Topology.id == topology_id).first()
    if not topology:
        raise HTTPException(status_code=404, detail="Topologia não encontrada")

    nodes = (
        db.query(models.TopologyNode)
        .filter(models.TopologyNode.topology_id == topology_id)
        .all()
    )
    edges = (
        db.query(models.TopologyEdge)
        .filter(models.TopologyEdge.topology_id == topology_id)
        .all()
    )

    def serialize_node(n):
        props = json.loads(n.props_json) if n.props_json else {}
        if not user.is_admin:
            props.pop("password", None)
        node_data = {
            "id": f"n{n.id}",
            "db_id": n.id,
            "label": n.label or "",
            "type": n.node_type,
            "color": n.color or "",
            "asset_id": n.asset_id,
            "props": props,
        }
        if n.parent_id:
            node_data["parent"] = f"n{n.parent_id}"
        result = {"data": node_data, "position": {"x": n.x or 0, "y": n.y or 0}}
        if n.width:
            result["style"] = {"width": n.width, "height": n.height or n.width}
        return result

    def serialize_edge(e):
        return {
            "data": {
                "id": f"e{e.id}",
                "db_id": e.id,
                "source": f"n{e.source_id}",
                "target": f"n{e.target_id}",
                "connection_type": e.connection_type or "unknown",
                "label": e.label or "",
                "color": e.color or "#8fabaf",
            }
        }

    return JSONResponse(
        {"nodes": [serialize_node(n) for n in nodes], "edges": [serialize_edge(e) for e in edges]}
    )


@router.post("/{topology_id}/save")
async def save_topology(topology_id: int, request: Request, db: Session = Depends(get_db)):
    csrf_token = request.headers.get("X-CSRF-Token")
    validate_csrf_token(request, csrf_token)

    user = get_session_user_record(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")

    topology = db.query(models.Topology).filter(models.Topology.id == topology_id).first()
    if not topology:
        raise HTTPException(status_code=404, detail="Topologia não encontrada")

    body = await request.json()
    nodes_data = body.get("nodes", [])
    edges_data = body.get("edges", [])

    db.query(models.TopologyEdge).filter(
        models.TopologyEdge.topology_id == topology_id
    ).delete()
    db.query(models.TopologyNode).filter(
        models.TopologyNode.topology_id == topology_id
    ).delete()
    db.flush()

    client_id_to_db_id: dict[str, int] = {}

    def _insert_node(n, parent_db_id):
        node = models.TopologyNode(
            topology_id=topology_id,
            asset_id=n.get("asset_id") or None,
            node_type=n.get("node_type", "desktop"),
            label=n.get("label", ""),
            x=float(n.get("x", 0)),
            y=float(n.get("y", 0)),
            width=float(n["width"]) if n.get("width") else None,
            height=float(n["height"]) if n.get("height") else None,
            color=n.get("color", ""),
            parent_id=parent_db_id,
            props_json=json.dumps(n.get("props", {})),
        )
        db.add(node)
        db.flush()
        client_id_to_db_id[n["client_id"]] = node.id

    for n in nodes_data:
        if not n.get("parent_client_id"):
            _insert_node(n, None)

    for n in nodes_data:
        if n.get("parent_client_id"):
            parent_db_id = client_id_to_db_id.get(n["parent_client_id"])
            _insert_node(n, parent_db_id)

    for e in edges_data:
        src = client_id_to_db_id.get(e.get("source_client_id", ""))
        tgt = client_id_to_db_id.get(e.get("target_client_id", ""))
        if not src or not tgt:
            continue
        db.add(
            models.TopologyEdge(
                topology_id=topology_id,
                source_id=src,
                target_id=tgt,
                connection_type=e.get("connection_type", "unknown"),
                label=e.get("label", ""),
                color=e.get("color", ""),
            )
        )

    topology.updated_at = utc_now()
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/{topology_id}/rename", response_class=HTMLResponse)
def rename_topology(
    topology_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(default=""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    topology = db.query(models.Topology).filter(models.Topology.id == topology_id).first()
    if not topology:
        raise HTTPException(status_code=404, detail="Topologia não encontrada")

    topology.name = name.strip() or topology.name
    topology.description = description.strip() or None
    db.commit()
    return RedirectResponse(url=f"/topology/{topology_id}", status_code=303)


@router.post("/{topology_id}/delete", response_class=HTMLResponse)
def delete_topology(
    topology_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    topology = db.query(models.Topology).filter(models.Topology.id == topology_id).first()
    if not topology:
        raise HTTPException(status_code=404, detail="Topologia não encontrada")

    db.query(models.TopologyEdge).filter(
        models.TopologyEdge.topology_id == topology_id
    ).delete()
    db.query(models.TopologyNode).filter(
        models.TopologyNode.topology_id == topology_id
    ).delete()
    db.delete(topology)
    db.commit()
    return RedirectResponse(url="/topology", status_code=303)
