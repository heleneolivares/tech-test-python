from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_GET

from portfolio.services import calculate_portfolio_evolution

# Create your views here.
def _parse_date(value: str | None) -> date:
    if not value:
        raise ValueError("Falta query param 'date' (formato esperado: YYYY-MM-DD).")
    try: 
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Formato de 'date' inválido. Usar YYYY-MM-DD") from exc
    
def _q(value: Decimal, decimals: int) -> Decimal: 
    exp = Decimal("1").scaleb(-decimals)
    return value.quantize(exp, rounding=ROUND_HALF_UP)

def _serialize_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    total_value: Decimal = item["total_value"]
    weights: dict[str, Decimal] = item["weights"]

    return {
        "date": item["date"].isoformat(),
        "total_value": str(_q(total_value,2)),
        "weights": {k: str(_q(v, 6)) for k, v in weights.items()},
    }
@require_GET
def portfolio_snapshot_view(request: HttpRequest, portfolio_id: int):
    try:
        d = _parse_date(request.GET.get("date"))

        data = calculate_portfolio_evolution(
            portfolio_id=portfolio_id,
            start_date=d,
            end_date=d,
        )

        if not data:
            return JsonResponse(
                {"detail": "No hay datos de precios/portafolio para esa fecha."},
                status = 404,
            )
        return JsonResponse(_serialize_snapshot(data[0]), status=200)
    
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Portafolio no encontrado"}, status=404)