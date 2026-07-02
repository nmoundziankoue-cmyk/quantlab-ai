"""Broker Connections router.

Endpoints:
  POST   /brokers                        Register a broker connection
  GET    /brokers                        List all broker connections
  GET    /brokers/{connection_id}        Get single connection
  PATCH  /brokers/{connection_id}        Update connection config
  DELETE /brokers/{connection_id}        Remove connection
  POST   /brokers/{connection_id}/test   Test / ping the connection
  GET    /brokers/types                  List supported broker types
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.trading import BrokerConnection, BrokerStatusEnum, BrokerTypeEnum
from schemas.trading import BrokerConnectionCreate, BrokerConnectionResponse, BrokerConnectionUpdate

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.get("/types", response_model=List[str])
def list_broker_types() -> List[str]:
    return [b.value for b in BrokerTypeEnum]


@router.post("", response_model=BrokerConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(body: BrokerConnectionCreate, db: Session = Depends(get_db)) -> BrokerConnectionResponse:
    connection = BrokerConnection(
        name=body.name,
        broker=BrokerTypeEnum(body.broker),
        is_paper=body.is_paper,
        credentials=body.credentials,
        config=body.config,
        status=BrokerStatusEnum.DISCONNECTED,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return BrokerConnectionResponse.model_validate(connection)


@router.get("", response_model=List[BrokerConnectionResponse])
def list_connections(db: Session = Depends(get_db)) -> List[BrokerConnectionResponse]:
    connections = db.query(BrokerConnection).order_by(BrokerConnection.created_at.desc()).all()
    return [BrokerConnectionResponse.model_validate(c) for c in connections]


@router.get("/{connection_id}", response_model=BrokerConnectionResponse)
def get_connection(connection_id: uuid.UUID, db: Session = Depends(get_db)) -> BrokerConnectionResponse:
    conn = db.query(BrokerConnection).filter(BrokerConnection.id == connection_id).first()
    if conn is None:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    return BrokerConnectionResponse.model_validate(conn)


@router.patch("/{connection_id}", response_model=BrokerConnectionResponse)
def update_connection(
    connection_id: uuid.UUID,
    body: BrokerConnectionUpdate,
    db: Session = Depends(get_db),
) -> BrokerConnectionResponse:
    conn = db.query(BrokerConnection).filter(BrokerConnection.id == connection_id).first()
    if conn is None:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if hasattr(conn, key) and val is not None:
            setattr(conn, key, val)
    db.commit()
    db.refresh(conn)
    return BrokerConnectionResponse.model_validate(conn)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    conn = db.query(BrokerConnection).filter(BrokerConnection.id == connection_id).first()
    if conn is None:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    db.delete(conn)
    db.commit()


@router.post("/{connection_id}/test", response_model=Dict[str, Any])
def test_connection(connection_id: uuid.UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    conn = db.query(BrokerConnection).filter(BrokerConnection.id == connection_id).first()
    if conn is None:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")

    broker_type = conn.broker.value if hasattr(conn.broker, "value") else conn.broker

    if broker_type == "PAPER":
        conn.status = BrokerStatusEnum.CONNECTED
        db.commit()
        return {"status": "connected", "broker": broker_type, "latency_ms": 0}

    try:
        from services.brokers import get_adapter
        adapter = get_adapter(broker_type, dict(conn.credentials), dict(conn.config))
        connected = adapter.connect()
        if connected:
            alive = adapter.ping()
            conn.status = BrokerStatusEnum.CONNECTED if alive else BrokerStatusEnum.ERROR
            db.commit()
            return {"status": "connected" if alive else "error", "broker": broker_type}
        else:
            conn.status = BrokerStatusEnum.ERROR
            conn.error_message = "connect() returned False"
            db.commit()
            return {"status": "error", "broker": broker_type, "message": "connect() returned False"}
    except NotImplementedError as exc:
        conn.status = BrokerStatusEnum.DISCONNECTED
        conn.error_message = str(exc)
        db.commit()
        return {
            "status": "not_implemented",
            "broker": broker_type,
            "message": str(exc),
        }
    except Exception as exc:
        conn.status = BrokerStatusEnum.ERROR
        conn.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Broker connection failed: {exc}")
