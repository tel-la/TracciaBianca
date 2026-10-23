"""Workflow locale per cartografia scialpinistica. Richiede il Python di QGIS."""

def classFactory(iface):
    from .provider import Plugin
    return Plugin(iface)
