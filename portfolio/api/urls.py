from django.urls import path

from portfolio.api.views import portfolio_snapshot_view

urlpatterns = [
    path(
        "portfolios/<int:portfolio_id>/snapshot/",
        portfolio_snapshot_view,
        name="portfolio-snapshot"
    ),
]