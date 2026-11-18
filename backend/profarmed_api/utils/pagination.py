from sqlalchemy.orm import Query
from typing import List, Dict, Any

def get_lookahead_pagination(
    query: Query,
    model_id_column: Any,
    skip: int,
    limit: int,
    max_lookahead: int = 5
) -> Dict[str, Any]:
    """
    Pagina una consulta usando lookahead.
    Evita counts masivos verificando si existen registros en offsets futuros por indices.
    """
    # 1. Obtener items de la página actual
    items = query.offset(skip).limit(limit).all()
    
    if len(items) < limit:
        return {"items": items, "lookahead_pages": 0}
        
    # 2. Verificar existencia de páginas siguientes
    lookahead_pages = 0
    for i in range(1, max_lookahead + 1):
        offset_to_check = skip + (limit * i)
        exists = query.with_entities(model_id_column).offset(offset_to_check).limit(1).first() is not None
        if exists:
            lookahead_pages = i
        else:
            break
            
    return {"items": items, "lookahead_pages": lookahead_pages}
