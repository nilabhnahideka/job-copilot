"""Shared FastAPI dependencies (things endpoints ask for in their arguments)."""

from fastapi import Request


def get_graph(request: Request):
    """The compiled agent graph, created once at startup (see main.lifespan)."""
    return request.app.state.graph
