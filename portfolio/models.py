from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

# Create your models here.


class BaseModel(models.Model):
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Portfolio(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    initial_value = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        db_table = "portfolio"
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Asset(BaseModel):
    ticker = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "asset"
        ordering = ['ticker']

    def __str__(self) -> str:
        return self.ticker


class PortfolioPosition(BaseModel):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="positions"
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="positions"
    )

    quantity = models.DecimalField(
        max_digits=30,
        decimal_places=10,
        validators=[MinValueValidator(0)]
    )

    class Meta: 
        db_table = 'portfolio_position'
        ordering = ['portfolio','asset']
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "asset"],
                name="portfolio_asset_unique",
            )
        ]
        indexes = [
            models.Index(fields=["portfolio","asset"], name="idx_portfolio_asset"),
        ]
    def __str__(self) -> str:
        return f"{self.portfolio} - {self.asset} ({self.quantity})"
    
class AssetPrice(BaseModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    date = models.DateField(db_index=True)
    price = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(0)])

    class Meta: 
        db_table = 'asset_price'
        ordering = ['asset', 'date']
        constraints = [
            models.UniqueConstraint(
                fields=["asset","date"],
                name="price_asset_date",
            )
        ]
        indexes = [
            models.Index(fields=["asset","date"], name="idx_asset_date"),
        ]
    def __str__(self) -> str :
        return f"{self.asset} @ {self.date} = {self.price}"
    